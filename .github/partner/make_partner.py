#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""협력사용 사용 설명서 생성기 — index.html(사내 설명서) → partner/index.html

GitHub Actions(.github/workflows/partner-guide.yml)가 사내 설명서가 바뀔 때마다 이 파일을 돌려 결과를 커밋한다.
사내 설명서만 고치면 협력사 페이지는 따라온다.

원칙
 1. 알려진 사내 전용 부분은 rules() 로 정확히 지우거나 고친다. 규칙이 가리키는 곳을 못 찾으면 실패한다
    (원본이 바뀌어 규칙이 낡았다는 뜻 — 조용히 넘어가면 사내 문구가 샐 수 있다).
 2. 변경 내역은 항목(li)마다 자동으로 거른다(사내 전용 낱말이 있으면 그 항목만 뺀다).
 3. 마지막에 결과 전체(화면 글자 + 소스 + data URI 안쪽)를 다시 검사해 사내 전용 낱말이 하나라도 남으면
    아무것도 쓰지 않고 실패한다 → 협력사 페이지는 마지막 정상본이 그대로 남는다(새는 것보다 늦는 게 낫다).

사용
  python3 .github/partner/make_partner.py            partner/ 에 쓴다
  python3 .github/partner/make_partner.py --check    쓰지 않고 검사만 — 사내 설명서를 올리기 전에 돌릴 것
  python3 .github/partner/make_partner.py --out DIR  DIR 에 쓴다(미리보기)
  … --site DIR                                       설명서 저장소 사본 위치를 직접 지정(이 파일이 저장소 밖에 있을 때)
표준 라이브러리만 쓴다(Actions 러너·Windows 둘 다 그대로 돈다).

★ 진행 상태(2026-11-10): 엔진 · 공통 단계 · 최종 검사 + 규칙 ①로그인 게이트 ②NAS 장 ③본문 17개(히어로 · #render · #layout ·
  #import · #shortcuts · #window · #start/#faq 의 NAS 항목)까지 있다. 로그인 안내 3곳과 사용자 결정에 걸린 곳이 남아 지금 돌리면 최종 검사에서 실패한다(3건).
  ★「✓ 검사 통과」는 끝이 아니다 — 검사는 금지 낱말과 게이트 흔적만 본다. 남은 일 전체는 census/audit_excerpts.py 가 센다.
  README.md 를 먼저 읽을 것.
"""
import base64
import html
import io
import os
import re
import sys
import unicodedata
import urllib.parse
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # 저장소 루트
SRC_INDEX = os.path.join(ROOT, 'index.html')
SRC_DEMO = os.path.join(ROOT, 'workflow-demo.html')

# ───────────────────────────── 낱말 검사 ─────────────────────────────
# 협력사 페이지(화면 글자·소스 전부)에 하나라도 있으면 실패. 변경 내역 항목 거르기에도 같은 목록을 쓴다.
LEAK = re.compile('|'.join([
    r'nas', r'나스', r'synology', r'시놀로지', r'(?<![a-z0-9])dsm(?![a-z0-9])', r'file\s*station', r'파일\s*스테이션',
    r'adarchive', r'애드\s*아카이브', r'ad\s*archive',
    r'wisebirds', r'와이즈버즈', r'접속\s*기록', r'경진대회', r'심사',
]), re.I)
# 로그인 게이트가 남았는지(협력사 페이지는 주소만 알면 연다 — 사용자 결정 2026-11-05)
GATE_LEFT = re.compile(r'authgate|gate-locked|accounts\.google\.com|gsi/client|google\.accounts|markerSet|ag-card'
                       r'|id="logout"|bn-guide-auth|JUDGE_|게이트', re.I)
# 2차 낱말 — 금지 낱말은 없지만 사내 사람에게만 맞는 표현. 본문 규칙을 다 쓴 뒤(2026-11-17) 잠갔다: 사내 설명서에 이런 표현이 새로 생기면
# 협력사 페이지는 실패해 마지막 정상본에 머문다 → 그 문장을 고치는 규칙을 rules() 에 더한다. 변경 내역 항목은 실패 대신 그 항목만 뺀다.
#   오탐 줄이기: 「검사내용」「회사내」의 사내 · 「실제보다」의 제보 · 「이동료」의 동료는 앞뒤 글자로 거른다.
STAFF = re.compile(r'(?<![가-힣])사내|영상팀|구성원|임직원|계열사|인트라넷|그룹웨어|adef\.co\.kr|ADEF\s*계정|구글|퇴사'
                   r'|(?<![가-힣])동료|(?<![가-힣])제보(?!다)|협력사|대행사|내부용|팀장', re.I)
# 패스워드 가리개가 묻는 서버(2026-11-24 사용자 결정 ① — 주소의 crnas 는 「보여도 괜찮다」). 최종 검사는 **이 글자 그대로만** 예외로 둔다.
GUIDE_API = 'https://crnas.adef.co.kr:8444/api/bnp/guide'
# 조사 결과의 고친 문구에 섞여 있는 자리표시([문의처 — 사용자 결정] 등) — 채우지 않고 넣으면 그대로 실린다
PLACEHOLDER = '사용자 결정]'


def leak_hits(text):
    return [(m.start(), m.group(0)) for m in LEAK.finditer(text)]


# ───────────────────────────── HTML 범위 트리 ─────────────────────────────
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr', 'param'}


class Node:
    __slots__ = ('tag', 'attrs', 's', 'se', 'es', 'e', 'parent', 'kids')

    def __init__(self, tag, attrs, s, se, parent):
        self.tag, self.attrs, self.s, self.se, self.parent = tag, attrs, s, se, parent
        self.es = self.e = None
        self.kids = []

    def cls(self):
        return (self.attrs.get('class') or '').split()

    def ancestors(self):
        p = self.parent
        while p is not None and p.tag != '#root':
            yield p
            p = p.parent


class Tree(HTMLParser):
    """요소마다 원문 오프셋 [s, e) 를 잡는다. 원문은 한 글자도 바꾸지 않는다(자를 범위만 계산)."""

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.lo = [0] + [m.end() for m in re.finditer('\n', text)]
        self.root = Node('#root', {}, 0, 0, None)
        self.stack = [self.root]
        self.all = []
        self.bad = []
        self.comments = []
        self.feed(text)
        self.close()
        if len(self.stack) > 1:
            self.bad.append('안 닫힌 요소: ' + ', '.join(n.tag for n in self.stack[1:]))

    def _pos(self):
        ln, col = self.getpos()
        return self.lo[ln - 1] + col

    def _add(self, tag, attrs, void):
        s = self._pos()
        raw = self.get_starttag_text()
        if not self.text.startswith(raw, s):
            self.bad.append('위치 어긋남 %s (%d줄)' % (tag, self.line(s)))
        n = Node(tag, {k: (v if v is not None else '') for k, v in attrs}, s, s + len(raw), self.stack[-1])
        self.stack[-1].kids.append(n)
        self.all.append(n)
        if void:
            n.es = n.e = n.se
        else:
            self.stack.append(n)

    def handle_starttag(self, tag, attrs):
        self._add(tag, attrs, tag in VOID)

    def handle_startendtag(self, tag, attrs):
        self._add(tag, attrs, True)

    def handle_comment(self, data):
        s = self._pos()
        self.comments.append((s, self.text.index('-->', s) + 3))

    def handle_endtag(self, tag):
        s = self._pos()
        e = self.text.index('>', s) + 1
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                if i != len(self.stack) - 1:
                    self.bad.append('암묵 닫힘 <%s> — </%s> 가 먼저 나옴 (%d줄)' % (self.stack[-1].tag, tag, self.line(s)))
                n = self.stack[i]
                n.es, n.e = s, e
                del self.stack[i:]
                return
        self.bad.append('짝 없는 닫는 태그 </%s> (%d줄)' % (tag, self.line(s)))

    # 질의
    def find(self, pred):
        return [n for n in self.all if pred(n)]

    def outer(self, n):
        return self.text[n.s:n.e]

    def inner(self, n):
        return self.text[n.se:n.es]

    def line(self, off):
        return self.text.count('\n', 0, off) + 1


def visible_text(fragment):
    """태그를 걷어 낸 글자(판정용). 스크립트·스타일 내용은 뺀다."""
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', fragment)
    t = re.sub(r'(?s)<!--.*?-->', ' ', t)
    t = re.sub(r'(?s)<[^>]+>', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


# ───────────────────────────── 선택자 ─────────────────────────────
def sel(tag=None, id=None, cls=None, attr=None, has=None, inside=None, text=None, nth=None):
    """작은 선택자. attr=(이름, 값|None) · has=원문 부분문자열 · text=화면 글자 부분문자열 · inside=조상 선택자(겹쳐 써도 된다).
    text 는 태그를 공백으로 바꾼 글자다(<b>가</b>나 → '가 나', &amp; 같은 문자 참조는 풀지 않는다).
    has/text 는 서로 포함된 요소 가운데 가장 안쪽만 고른다 → tag 와 cls 를 같이 줄 것. nth=걸린 것 가운데 n번째(1부터)."""
    def pred(n, _t=None):
        if tag and n.tag != tag:
            return False
        if id and n.attrs.get('id') != id:
            return False
        if cls and cls not in n.cls():
            return False
        if attr:
            k, v = attr
            if k not in n.attrs or (v is not None and n.attrs.get(k) != v):
                return False
        return True
    pred.has, pred.text, pred.inside, pred.nth = has, text, inside, nth
    pred.desc = ' '.join(x for x in [tag or '', ('#' + id) if id else '', ('.' + cls) if cls else '',
                                       ('[%s=%s]' % attr) if attr else '', ('∋원문 ' + repr(has)) if has else '',
                                       ('∋글자 ' + repr(text)) if text else '', ('⊂(' + inside.desc + ')') if inside else '',
                                       ('%d번째' % nth) if nth else ''] if x)
    return pred


def _match(tree, n, p):
    """n 이 선택자 p 에 맞는가 — has · text · inside(여러 단계) 까지 본다."""
    if not p(n):
        return False
    if p.has is not None and p.has not in tree.outer(n):
        return False
    if p.text is not None and p.text not in visible_text(tree.outer(n)):
        return False
    if p.inside is not None and not any(_match(tree, a, p.inside) for a in n.ancestors()):
        return False
    return True


def query(tree, p):
    out = [n for n in tree.all if _match(tree, n, p)]
    # 서로 포함된 것은 가장 안쪽만(같은 글자를 품은 조상까지 다 잡히지 않게) — has/text 질의일 때만
    if p.has is not None or p.text is not None:
        inner = []
        for n in out:
            if not any(m is not n and m.s >= n.s and m.e <= n.e for m in out):
                inner.append(n)
        out = inner
    if p.nth is not None:
        out = out[p.nth - 1:p.nth]
    return out


# ───────────────────────────── 편집 ─────────────────────────────
class Fail(Exception):
    pass


def eat_blank_line(text, s, e):
    """지운 요소가 줄 하나를 통째로 차지했으면 그 줄(앞 들여쓰기 + 뒤 줄바꿈)까지 같이 지운다."""
    ls = text.rfind('\n', 0, s) + 1
    if text[ls:s].strip() == '':
        le = text.find('\n', e)
        le = len(text) if le < 0 else le
        if text[e:le].strip() == '':
            return ls, min(le + 1, len(text))
    return s, e


def apply_edits(text, edits):
    """edits = [(s, e, new)] — 겹치면 실패, 포함되면 바깥 것만."""
    edits = sorted(edits, key=lambda x: (x[0], x[0] != x[1], -x[1]))   # 같은 자리에서는 끼워 넣기(폭 0)가 먼저
    keep = []
    for s, e, new in edits:
        if keep and s < keep[-1][1]:
            if e <= keep[-1][1]:
                continue        # 바깥 편집이 이미 덮는다
            raise Fail('편집 범위가 겹칩니다 @%d' % s)
        keep.append((s, e, new))
    for s, e, new in reversed(keep):
        text = text[:s] + new + text[e:]
    return text


class Doc:
    def __init__(self, text, name):
        self.text, self.name = text, name
        self.log = []

    def tree(self):
        t = Tree(self.text)
        if t.bad:
            raise Fail('%s HTML 구조 이상: %s%s' % (self.name, '; '.join(t.bad[:5]),
                                                 ('\n  직전에 적용한 규칙(이 규칙이 구조를 깼을 수 있습니다): ' + self.log[-1]) if self.log else ''))
        return t

    def _frag(self, html, p, what):
        """넣으려는 HTML 조각이 스스로 닫혀 있는지 — 깨진 조각은 넣는 자리에서 바로 실패시킨다."""
        bad = Tree(html).bad
        if bad:
            raise Fail('%s %s — 넣으려는 HTML 이 닫히지 않았습니다(%s): %s' % (self.name, what, p.desc, '; '.join(bad[:3])))

    def _same(self, t, hits, old, what, inner):
        """통째로 바꾸는 규칙의 안전장치 — 원본 요소의 글(공백은 접어서 비교)이 규칙을 쓸 때(old)와 같은지 본다."""
        if old is None:
            return
        fold = lambda x: re.sub(r'\s+', ' ', x).strip()
        for n in hits:
            if fold(t.inner(n) if inner else t.outer(n)) != fold(old):
                raise Fail('%s 규칙이 낡았습니다 — %s: 원본 요소의 글이 규칙을 쓸 때와 다릅니다(%d줄). 바뀐 원문을 보고 규칙을 다시 쓸 것' % (self.name, what, t.line(n.s)))

    def _hits(self, p, count, what):
        t = self.tree()
        hits = query(t, p)
        if (count is not None and len(hits) != count) or (count is None and not hits):
            where = ''.join('\n    · %d줄: %s' % (t.line(n.s), re.sub(r'\s+', ' ', t.outer(n))[:90]) for n in hits[:6])
            raise Fail('%s 규칙이 맞지 않습니다 — %s: 기대 %s곳, 실제 %d곳 (%s)%s\n'
                       '  새로 쓴 규칙이면 선택자와 count 를 고친다(걸린 줄은 앞 규칙들을 적용한 뒤의 글 기준). '
                       '전에 통과하던 규칙이면 원본(사내 설명서)이 바뀐 것이다 — 바뀐 문구를 보고 규칙을 다시 쓴다.'
                       % (self.name, what, '1곳 이상' if count is None else count, len(hits), p.desc, where))
        return t, hits

    def drop(self, p, count=1, why=''):
        t, hits = self._hits(p, count, '지우기')
        self.text = apply_edits(self.text, [eat_blank_line(self.text, n.s, n.e) + ('',) for n in hits])
        self.log.append('지움 %d · %s · %s' % (len(hits), p.desc, why))

    def unwrap(self, p, count=1, why=''):
        """요소 껍데기만 벗기고 안은 남긴다."""
        t, hits = self._hits(p, count, '껍데기 벗기기')
        self.text = apply_edits(self.text, [(n.s, n.e, self.text[n.se:n.es]) for n in hits])
        self.log.append('벗김 %d · %s · %s' % (len(hits), p.desc, why))

    def set_inner(self, p, html, count=1, why='', old=None):
        """요소 안쪽을 통째로 바꾼다. old=규칙을 쓸 때의 원문 안쪽 을 주면 원본이 그 뒤로 바뀌었을 때 실패한다(안 주면 원본의 새 수정이 조용히 덮인다)."""
        self._frag(html, p, '안쪽 바꾸기')
        t, hits = self._hits(p, count, '안쪽 바꾸기')
        self._same(t, hits, old, '안쪽 바꾸기', True)
        self.text = apply_edits(self.text, [(n.se, n.es, html) for n in hits])
        self.log.append('바꿈 %d · %s · %s' % (len(hits), p.desc, why))

    def set_outer(self, p, html, count=1, why='', old=None):
        """요소를 통째로 바꾼다. old=규칙을 쓸 때의 원문 요소 를 주면 원본이 그 뒤로 바뀌었을 때 실패한다."""
        self._frag(html, p, '통째로 바꾸기')
        t, hits = self._hits(p, count, '통째로 바꾸기')
        self._same(t, hits, old, '통째로 바꾸기', False)
        self.text = apply_edits(self.text, [(n.s, n.e, html) for n in hits])
        self.log.append('교체 %d · %s · %s' % (len(hits), p.desc, why))

    def insert(self, p, html, where='after', count=1, why=''):
        self._frag(html, p, '끼워 넣기')
        t, hits = self._hits(p, count, '끼워 넣기')
        eds = []
        for n in hits:
            pos = {'before': n.s, 'after': n.e, 'prepend': n.se, 'append': n.es}[where]
            eds.append((pos, pos, html))
        self.text = apply_edits(self.text, eds)
        self.log.append('넣음 %d · %s(%s) · %s' % (len(hits), p.desc, where, why))

    def sub(self, old, new, count=1, why='', inside=None, optional=False):
        """정확한 글자 바꾸기 — 기대 횟수와 다르면 실패(원본 문구가 바뀌었다는 뜻).
        원문 전체(스크립트·CSS·변경 내역 포함)에서 센다. inside=선택자 를 주면 그 요소(들) 안에서만 세고 바꾼다.
        optional=True — 「있으면 지우는」 규칙에만 쓴다: 0곳이면 실패하지 않고 넘어간다(사내 설명서가 그 문장을 스스로 뺀 경우).
        남으면 새는 글이 아니라 「있어도 그만인 옛 이력」에만 쓸 것 — 금지 낱말이 든 문장은 어차피 최종 검사가 막는다."""
        if inside is not None:
            t, hits = self._hits(inside, None, '글자 바꾸기 범위')
            hits = [n for n in hits if not any(m is not n and m.s <= n.s and n.e <= m.e for m in hits)]   # 겹치면 바깥 것만
            c = sum(self.text[n.s:n.e].count(old) for n in hits)
            if optional and c == 0:
                self.log.append('건너뜀(원본에 이미 없음) · %r · %s' % (old[:40], why))
                return
            if c != count:
                raise Fail('%s 규칙이 낡았습니다 — 글자 바꾸기: 기대 %d곳, 실제 %d곳 %r (범위 %s)' % (self.name, count, c, old[:80], inside.desc))
            self.text = apply_edits(self.text, [(n.s, n.e, self.text[n.s:n.e].replace(old, new)) for n in hits])
            self.log.append('글자 %d · %r → %r ⊂(%s) · %s' % (c, old[:40], new[:40], inside.desc, why))
            return
        c = self.text.count(old)
        if c != count:
            raise Fail('%s 규칙이 낡았습니다 — 글자 바꾸기: 기대 %d곳, 실제 %d곳 %r' % (self.name, count, c, old[:80]))
        self.text = self.text.replace(old, new)
        self.log.append('글자 %d · %r → %r · %s' % (c, old[:40], new[:40], why))

    def set_attr(self, p, name, value, count=1, why=''):
        """여는 태그의 속성 하나를 넣거나 바꾼다(value=None 이면 뺀다). 태그의 나머지 글자는 그대로 둔다."""
        t, hits = self._hits(p, count, '속성 바꾸기')
        pat = re.compile(r'(\s+)%s(?:\s*=\s*(?:"[^"]*"|\'[^\']*\'|[^\s>]+))?(?=\s|/?>)' % re.escape(name), re.I)
        eds = []
        for n in hits:
            tag = self.text[n.s:n.se]
            if value is None and name not in n.attrs:
                raise Fail('%s 규칙이 낡았습니다 — 속성 빼기: %s 에 %s 속성이 없습니다' % (self.name, p.desc, name))
            attr = '' if value is None else '%s="%s"' % (name, value.replace('&', '&amp;').replace('"', '&quot;'))
            if name in n.attrs:      # 있는 속성을 바꾸거나 뺀다 — 후보(같은 글자가 다른 속성 값 안에 있을 수도 있다)마다 고쳐 보고
                cands = [tag[:m.start()] + ((m.group(1) + attr) if attr else '') + tag[m.end():] for m in pat.finditer(tag)]
            else:
                cut = len(tag) - (2 if tag.endswith('/>') else 1)
                cands = [tag[:cut].rstrip() + ' ' + attr + (' />' if tag.endswith('/>') else '>')]
            want = dict(n.attrs)
            want.pop(name, None)
            if value is not None:
                want[name] = value
            new = None
            for c in cands:          # 다시 읽어서 「그 속성만」 뜻대로 바뀐 후보를 쓴다
                chk = Tree(c)
                if chk.all and chk.all[0].tag == n.tag and chk.all[0].attrs == want:
                    new = c
                    break
            if new is None:
                raise Fail('%s 속성 바꾸기 실패 — 여는 태그를 안전하게 고치지 못했습니다: %s' % (self.name, tag[:120]))
            eds.append((n.s, n.se, new))
        self.text = apply_edits(self.text, eds)
        self.log.append('속성 %d · %s %s=%r · %s' % (len(hits), p.desc, name, value, why))

    def css_drop(self, rule_pred, why=''):
        """모든 <style> 안에서 선택자가 rule_pred 에 걸리는 CSS 규칙을 지운다(@media 안쪽까지)."""
        t = self.tree()
        eds, n_rules = [], 0
        for st in [n for n in t.all if n.tag == 'style']:
            body = self.text[st.se:st.es]
            new, k = filter_css(body, rule_pred)
            if k:
                eds.append((st.se, st.es, new))
                n_rules += k
        if not n_rules:
            raise Fail('%s 규칙이 낡았습니다 — CSS 지우기 0건 (%s)' % (self.name, why))
        self.text = apply_edits(self.text, eds)
        self.log.append('CSS 규칙 %d개 지움 · %s' % (n_rules, why))


# ───────────────────────────── CSS ─────────────────────────────
def _css_blocks(css):
    """최상위 규칙을 (머리, 몸, 시작, 끝) 으로 나눈다. 주석·문자열 안의 괄호는 무시."""
    out, i, n, start = [], 0, len(css), 0
    depth, head_start, body_start = 0, 0, None
    while i < n:
        c = css[i]
        if css.startswith('/*', i):
            j = css.find('*/', i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in '"\'':
            j = i + 1
            while j < n and css[j] != c:
                j += 2 if css[j] == '\\' else 1
            i = j + 1
            continue
        if c == '{':
            if depth == 0:
                body_start = i
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                out.append((css[head_start:body_start], css[body_start + 1:i], head_start, i + 1))
                head_start = i + 1
        elif c == ';' and depth == 0:
            head_start = i + 1      # @import 같은 한 줄 규칙
        i += 1
    return out


def _split_selectors(h):
    """선택자 목록을 최상위 쉼표에서만 나눈다 — (), [], 따옴표 안의 쉼표는 그대로 둔다."""
    parts, depth, q, start, i = [], 0, None, 0, 0
    while i < len(h):
        c = h[i]
        if q:
            if c == '\\':
                i += 1
            elif c == q:
                q = None
        elif c in '"\'':
            q = c
        elif c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        elif c == ',' and depth == 0:
            parts.append(h[start:i])
            start = i + 1
        i += 1
    parts.append(h[start:])
    return [x.strip() for x in parts]


def filter_css(css, pred):
    """pred(선택자 문자열) 가 참인 규칙을 지운 css 와 지운 수. 쉼표 목록은 걸린 선택자만 빼고 나머지는 남긴다."""
    blocks = _css_blocks(css)
    eds, k = [], 0
    for head, body, s, e in blocks:
        h = re.sub(r'/\*.*?\*/', '', head, flags=re.S).strip()
        if re.match(r'@(media|supports|container|layer)\b', h):
            nb, kk = filter_css(body, pred)
            if kk:
                k += kk
                if not _css_blocks(nb) and not nb.strip():
                    eds.append((s, e, ''))
                elif not _css_blocks(nb):
                    eds.append((s, e, ''))
                else:
                    eds.append((s, e, head + '{' + nb + '}'))
            continue
        if h.startswith('@'):
            continue
        parts = _split_selectors(h)
        bad = [x for x in parts if pred(x)]
        if not bad:
            continue
        k += 1
        if len(bad) == len(parts):
            m = re.match(r'[ \t]*/\*.*?\*/', css[e:], re.S)     # 지운 규칙과 같은 줄에 붙은 꼬리 주석(그 규칙의 설명)도 함께
            eds.append((s, e + m.end() if m and '\n' not in m.group(0) else e, ''))
        else:
            lead = head[:len(head) - len(head.lstrip())]
            eds.append((s, e, lead + ', '.join(x for x in parts if not pred(x)) + '{' + body + '}'))
    for s, e, new in sorted(eds, reverse=True):
        css = css[:s] + new + css[e:]
    return css, k


# ───────────────────────────── 버전 ─────────────────────────────
def ver_tuple(v):
    m = re.search(r'(\d+)\.(\d+)\.(\d+)', v or '')
    return tuple(int(x) for x in m.groups()) if m else None


# ───────────────────────────── 최종 검사 ─────────────────────────────
DATA_URI = re.compile(r'data:([a-z]+/[a-z0-9.+-]+)?((?:;[a-z0-9-]+=[^;,]+)*)(;base64)?,([^"\')\s]*)', re.I)   # mime 이 없으면 text/plain(RFC 2397)
_INLINE_BARE = re.compile(r'(?i)</?(?:b|i|u|s|em|strong|small|mark|span|font|wbr)\s*>|[\u00ad\u200b\u200c\u200d\ufeff]')
_CSS_URL = re.compile(r'(?i)url\(\s*["\']?([^"\')\s]+)')


def _local_ref(u):
    """같은 사이트의 상대 경로인가(#앵커 · http(s): · data: · mailto: · // 는 아니다)."""
    u = (u or '').strip()
    return bool(u) and not u.startswith('#') and not u.startswith('//') and not re.match(r'(?i)[a-z][a-z0-9+.-]*:', u)


def _orig_line(orig, text, off):
    """결과의 off 가 있는 줄이 원본에 그대로 있으면 그 원본 줄 번호들('716·745') — 없거나 너무 많으면 ''."""
    ls = text.rfind('\n', 0, off) + 1
    le = text.find('\n', off)
    line = text[ls:len(text) if le < 0 else le]
    if orig is None or not line.strip():
        return ''
    nums = [i + 1 for i, l in enumerate(orig.split('\n')) if l == line]
    return '·'.join(map(str, nums)) if 1 <= len(nums) <= 3 else ''


def final_gate(text, name, required_ids=(), files=None, orig=None):
    """files=같은 폴더에 함께 쓰는 파일 이름들(주면 상대 경로 자원이 거기 있는지 본다) · orig=원본 글(주면 원본 줄 번호를 덧붙인다)."""
    problems = []
    # data URI 안쪽: 글자형(svg·text·css·json·js)은 풀어서 검사, 나머지(글꼴·그림)는 무작위 base64 라 뺀다
    scan = text
    for m in reversed(list(DATA_URI.finditer(text))):
        mime, b64, payload = (m.group(1) or 'text/plain').lower(), m.group(3), m.group(4)
        if mime.startswith('text/') or mime in ('image/svg+xml', 'application/json', 'application/javascript'):
            try:
                dec = base64.b64decode(payload).decode('utf-8', 'replace') if b64 else urllib.parse.unquote(payload)
            except Exception as ex:   # 못 푸는 글자형 data URI 는 검사를 못 하니 실패로
                problems.append('%s data URI(%s)를 풀지 못했습니다: %s' % (name, mime, ex))
                dec = ''
            for off, w in leak_hits(dec) + [(m.start(), m.group(0)) for m in STAFF.finditer(dec)]:
                problems.append('%s data URI(%s) 안에 %r — %r' % (name, mime, w, dec[max(0, off - 30):off + 30]))
        scan = scan[:m.start(4)] + '·' * len(payload) + scan[m.end(4):]
    scan = scan.replace(GUIDE_API, '·' * len(GUIDE_API))   # 가리개의 서버 주소 한 줄만 예외(같은 길이로 가려 줄 번호 유지)
    raw_hits = leak_hits(scan)
    for off, w in raw_hits:
        ln = text.count('\n', 0, off) + 1
        ol = _orig_line(orig, text, off)
        problems.append('%s %d줄%s %r — %r' % (name, ln, ('(원본 %s줄)' % ol) if ol else '', w, scan[max(0, off - 40):off + 40].replace('\n', ' ')))
    if not raw_hits:
        # 그대로는 안 보이는 표기를 풀어서 다시 본다 — %인코딩 · 문자 참조(&#78;AS) · 자모 분리(NFD)·전각 · 꾸밈 태그로 쪼갠 글자(<b>N</b>AS)
        for how, v in (('%인코딩을 풀면', urllib.parse.unquote(scan)),
                       ('문자 참조를 풀면', html.unescape(scan)),
                       ('유니코드 정규화(NFKC)하면', unicodedata.normalize('NFKC', scan)),
                       ('꾸밈 태그를 걷으면', html.unescape(_INLINE_BARE.sub('', scan)))):
            for off, w in leak_hits(v):
                problems.append('%s %s %r — %r' % (name, how, w, v[max(0, off - 40):off + 40].replace('\n', ' ')))
    if not STAFF.search(scan):
        for how, v in (('문자 참조를 풀면', html.unescape(scan)),
                       ('유니코드 정규화(NFKC)하면', unicodedata.normalize('NFKC', scan)),
                       ('꾸밈 태그를 걷으면', html.unescape(_INLINE_BARE.sub('', scan)))):
            for m in STAFF.finditer(v):
                problems.append('%s %s 사내 표현 %r — %r' % (name, how, m.group(0), v[max(0, m.start() - 40):m.start() + 40].replace('\n', ' ')))
    for m in STAFF.finditer(scan):
        ln = text.count('\n', 0, m.start()) + 1
        ol = _orig_line(orig, text, m.start())
        problems.append('%s %d줄%s 사내 표현 %r — %r' % (name, ln, ('(원본 %s줄)' % ol) if ol else '', m.group(0),
                                                    scan[max(0, m.start() - 40):m.start() + 40].replace('\n', ' ')))
    for m in GATE_LEFT.finditer(scan):
        problems.append('%s 로그인 게이트 흔적 %r (%d줄)' % (name, m.group(0), text.count('\n', 0, m.start()) + 1))
    if PLACEHOLDER in scan:
        problems.append('%s 자리표시가 남았습니다(「… — 사용자 결정]」 %d곳) — 사용자 답으로 채울 것' % (name, scan.count(PLACEHOLDER)))
    t = Tree(text)
    if t.bad:
        problems.append('%s HTML 구조 이상: %s' % (name, '; '.join(t.bad[:5])))
    ids = {n.attrs.get('id') for n in t.all if n.attrs.get('id')}
    for rid in required_ids:
        if rid not in ids:
            problems.append('%s 필수 id #%s 없음(앱이 이 앵커로 엽니다)' % (name, rid))
    for n in t.all:
        h = n.attrs.get('href') or ''
        if n.tag == 'a' and h.startswith('#') and len(h) > 1 and h[1:] not in ids:
            problems.append('%s 깨진 링크 %s (%d줄)' % (name, h, t.line(n.s)))
    if files is not None:
        # 협력사 폴더에는 생성기가 쓰는 파일만 있다 — 원본에 새 그림·스크립트가 상대 경로로 생기면 협력사 쪽에서는 404 가 된다
        refs = []
        for n in t.all:
            for k in ('src', 'href', 'poster', 'data', 'action'):
                if k in n.attrs:
                    refs.append((n.attrs[k], n.s))
            for part in (n.attrs.get('srcset') or '').split(','):
                if part.strip():
                    refs.append((part.split()[0], n.s))
            for u in _CSS_URL.findall(n.attrs.get('style') or ''):
                refs.append((u, n.s))
            if n.tag == 'style' and n.es is not None:
                for u in _CSS_URL.findall(text[n.se:n.es]):
                    refs.append((u, n.s))
        for u, pos in refs:
            if _local_ref(u) and re.split(r'[?#]', u.strip())[0] not in files:
                problems.append('%s 협력사 폴더에 없는 상대 경로 %r (%d줄) — 함께 쓰는 파일: %s' % (name, u[:80], t.line(pos), ', '.join(sorted(files))))
    return problems


# ───────────────────────────── 공통 단계 ─────────────────────────────
PARTNER_SINCE = (1, 0, 204)   # 협력사 첫 배포판 — 변경 내역은 이 판부터 보여 준다(그 전 판은 사내 이력)
NO_CHANGE_NOTE = '<li><small>사용 방법·기능은 이전 판과 같습니다.</small></li>'


def _plain(x):
    """낱말 판정용 — 문자 참조 · 전각/자모 분리 · 꾸밈 태그로 끊긴 글자를 풀어 놓은 글."""
    return html.unescape(_INLINE_BARE.sub('', unicodedata.normalize('NFKC', x)))


def filter_changelog(doc):
    """판(details.cl-entry)은 PARTNER_SINCE 부터만, 항목(li)은 사내 전용 낱말이 있으면 뺀다.
    보이는 항목이 하나도 안 남는 판은 판은 남기고 한 줄 안내로 바꾼다(판 번호가 이어지게).
    남는 판이 없으면 섹션째 뺀다(목차는 sync_toc 가 맞춘다)."""
    t = doc.tree()
    sec = query(t, sel('section', id='changelog'))
    if len(sec) != 1:
        raise Fail('변경 내역 섹션(#changelog)이 %d개입니다' % len(sec))
    sec = sec[0]
    entries = [n for n in t.all if n.tag == 'details' and 'cl-entry' in n.cls() and sec.s <= n.s < sec.e]
    if not entries:
        raise Fail('변경 내역 판(details.cl-entry)을 못 찾았습니다')
    eds, kept, gone_items, dropped = [], 0, 0, []
    for en in entries:
        vs = [n for n in t.all if n.tag == 'span' and 'cl-ver' in n.cls() and en.s <= n.s < en.e]
        v = ver_tuple(t.inner(vs[0])) if vs else None
        if v is None:
            raise Fail('변경 내역 판 번호를 못 읽었습니다 (%d줄)' % t.line(en.s))
        if v < PARTNER_SINCE:
            eds.append(eat_blank_line(doc.text, en.s, en.e) + ('',))
            continue
        kept += 1
        lis = [n for n in t.all if n.tag == 'li' and en.s <= n.s < en.e]
        bad = [li for li in lis if LEAK.search(_plain(t.outer(li))) or STAFF.search(_plain(t.outer(li)))]
        for li in bad:
            w = (LEAK.search(_plain(t.outer(li))) or STAFF.search(_plain(t.outer(li)))).group(0)
            dropped.append('%s 항목 뺌(%r): %s' % (t.inner(vs[0]), w, ' '.join(visible_text(t.inner(li)).split())[:70]))
        real = [li for li in lis if not re.fullmatch(r'\s*<small>.*</small>\s*', t.inner(li), re.S)]
        if bad and all(li in bad for li in real):
            uls = [n for n in t.all if n.tag == 'ul' and en.s <= n.s < en.e]
            if len(uls) != 1:
                raise Fail('변경 내역 %s 의 목록(ul)이 %d개입니다' % (t.inner(vs[0]), len(uls)))
            ind = doc.text[doc.text.rfind('\n', 0, lis[0].s) + 1:lis[0].s]
            eds.append((uls[0].se, uls[0].es, '\n\n' + ind + NO_CHANGE_NOTE + '\n\n' + ind[:-2] if len(ind) >= 2 else '\n' + NO_CHANGE_NOTE + '\n'))
            gone_items += len(lis)
            dropped.append('⚠ %s 판의 항목이 전부 빠져 「이전 판과 같습니다」 한 줄로 바뀝니다 — 릴리즈 노트 낱말을 확인할 것' % t.inner(vs[0]))
        else:
            for li in bad:
                eds.append(eat_blank_line(doc.text, li.s, li.e) + ('',))
            gone_items += len(bad)
    if kept == 0:
        doc.text = apply_edits(doc.text, [eat_blank_line(doc.text, sec.s, sec.e) + ('',)])
        doc.log.append('변경 내역: %s 이상 판이 아직 없어 섹션을 뺐습니다(원본 %d판)' % ('.'.join(map(str, PARTNER_SINCE)), len(entries)))
        return
    doc.text = apply_edits(doc.text, eds)
    # 판을 지운 자리에 빈 줄이 수십 줄 남는다(소스에서 「잘려 나간 자리」가 보인다) → 장 안의 연속 빈 줄을 한 줄로 접는다
    t = doc.tree()
    sec = query(t, sel('section', id='changelog'))[0]
    body = doc.text[sec.s:sec.e]
    doc.text = doc.text[:sec.s] + re.sub(r'\n(?:[ \t]*\n){2,}', '\n\n', body) + doc.text[sec.e:]
    doc.log.append('변경 내역: %d판 중 %d판 보임 · 항목 %d개 뺌' % (len(entries), kept, gone_items))
    doc.log += ['변경 내역: ' + x for x in dropped]


def strip_comments(doc):
    """HTML 주석은 전부 뺀다(화면엔 안 보이지만 소스에 사내 메모가 남지 않게). 스크립트·스타일 안쪽은 건드리지 않는다."""
    t = doc.tree()
    if t.comments:
        doc.text = apply_edits(doc.text, [eat_blank_line(doc.text, s, e) + ('',) for s, e in t.comments])
    doc.log.append('HTML 주석 %d개 뺌' % len(t.comments))


_RX_PREV = set('(,=:[!&|?{};+-*%<>~^')      # 이 글자 뒤(또는 줄 처음 · return 뒤)의 / 는 나눗셈이 아니라 정규식의 시작


def strip_js_comments(js, what):
    """스크립트의 // · /* */ 주석만 뺀다(문자열 · 템플릿 · 정규식 안은 그대로). 끝까지 못 읽으면 실패 — 추측으로 지우지 않는다.
    주석만 있던 줄은 줄째 빼고, 코드 뒤 주석은 앞 공백까지 뺀다. 코드 글자는 한 자도 바꾸지 않는다."""
    out, i, n = [], 0, len(js)
    prev = ''          # 직전의 공백 아닌 코드 글자
    prev2 = ''         # 그 앞 글자(++ · -- 판별)
    word = ''          # 직전 토큰이 낱말일 때 그 낱말(return · typeof 뒤의 / 는 정규식). 기호를 만나면 비운다
    while i < n:
        c = js[i]
        two = js[i:i + 2]
        if two == '//':
            j = js.find('\n', i)
            j = n if j < 0 else j
            k = len(out)
            while k and out[k - 1] in ' \t':
                k -= 1
            del out[k:]
            if (not out or out[-1] == '\n') and j < n:
                j += 1                      # 주석만 있던 줄 — 줄바꿈까지
            i = j
            continue
        if two == '/*':
            j = js.find('*/', i + 2)
            if j < 0:
                raise Fail('%s 스크립트의 /* 주석이 닫히지 않았습니다' % what)
            if out and (out[-1][-1:].isalnum() or out[-1][-1:] in '_$') and j + 2 < n and (js[j + 2].isalnum() or js[j + 2] in '_$'):
                out.append(' ')             # 주석이 두 낱말 사이의 유일한 구분자였다 — 붙지 않게 한 칸
            i = j + 2
            continue
        if c in '"\'`':
            j = i + 1
            while j < n and js[j] != c:
                if js[j] == '\\':
                    j += 1
                elif c == '`' and js[j:j + 2] == '${':
                    # 템플릿의 ${ 식 } — 식 안에 백틱(겹친 템플릿)이나 주석 표시가 없을 때만 그대로 건너뛴다. 있으면 추측하지 않고 멈춘다
                    k, depth = j + 2, 1
                    while k < n and depth:
                        depth += (js[k] == '{') - (js[k] == '}')
                        k += 1
                    expr = js[j + 2:k - 1]
                    if depth or '`' in expr or '//' in expr or '/*' in expr:
                        raise Fail('%s 스크립트의 템플릿 문자열 ${ } 안에 겹친 템플릿이나 주석 표시가 있습니다 — 주석 제거기가 다루지 못하는 꼴이라 멈춥니다'
                                   '(make_partner.py strip_js_comments 를 넓히거나 그 줄을 문자열 더하기로 쓸 것): %r…' % (what, js[j:j + 40]))
                    j = k - 1
                elif js[j] == '\n' and c != '`':
                    raise Fail('%s 스크립트의 문자열이 줄 안에서 닫히지 않았습니다(%r…)' % (what, js[i:i + 40]))
                j += 1
            if j >= n:
                raise Fail('%s 스크립트의 문자열이 닫히지 않았습니다(%r…)' % (what, js[i:i + 40]))
            out.append(js[i:j + 1])
            prev2, prev, word, i = prev, c, '', j + 1
            continue
        if c == '/' and (prev == '' or (prev in _RX_PREV and not (prev in '+-' and prev2 == prev))
                         or word in ('return', 'typeof', 'case', 'void', 'delete', 'throw', 'else', 'do')):
            j, incls = i + 1, False
            while j < n and (js[j] != '/' or incls):
                if js[j] == '\\':
                    j += 1
                elif js[j] == '[':
                    incls = True
                elif js[j] == ']':
                    incls = False
                elif js[j] == '\n':
                    raise Fail('%s 스크립트의 정규식이 줄 안에서 닫히지 않았습니다(%r…)' % (what, js[i:i + 40]))
                j += 1
            if j >= n:
                raise Fail('%s 스크립트의 정규식이 닫히지 않았습니다(%r…)' % (what, js[i:i + 40]))
            out.append(js[i:j + 1])
            prev2, prev, word, i = prev, '/', '', j + 1
            continue
        out.append(c)
        if not c.isspace():
            if c.isalnum() or c in '_$':
                word = (word + c) if (i and (js[i - 1].isalnum() or js[i - 1] in '_$')) else c   # 바로 붙은 글자만 같은 낱말
            else:
                word = ''
            prev2, prev = prev, c
        i += 1
    res = ''.join(out)
    # 값싼 불변식 — 코드 글자를 건드리지 않았다면 따옴표 · 괄호 수는 「주석 안에 있던 것」만큼만 줄어든다. 늘었으면 잘못 지운 것이다
    for ch in '(){}[]`':
        if res.count(ch) > js.count(ch):
            raise Fail('%s 스크립트 주석 제거 뒤 %r 수가 늘었습니다' % (what, ch))
    if res.count('`') % 2:
        raise Fail('%s 스크립트 주석 제거 뒤 백틱이 짝이 맞지 않습니다' % what)
    return res


def strip_css_comments(css, what):
    out, i, n = [], 0, len(css)
    while i < n:
        c = css[i]
        if css[i:i + 2] == '/*':
            j = css.find('*/', i + 2)
            if j < 0:
                raise Fail('%s 스타일의 /* 주석이 닫히지 않았습니다' % what)
            k = len(out)
            while k and out[k - 1] in ' \t':
                k -= 1
            if out[:k] and (out[k - 1][-1:].isalnum() or out[k - 1][-1:] in '_-') and j + 2 < n and (css[j + 2].isalnum() or css[j + 2] in '_-.#'):
                out.insert(k, ' ')
                k += 1
            ls = css.rfind('\n', 0, i) + 1
            if css[ls:i].strip() == '' and css[j + 2:css.find('\n', j + 2) if css.find('\n', j + 2) >= 0 else n].strip() == '':
                del out[k:]                 # 주석만 있던 줄 — 줄째
                j2 = css.find('\n', j + 2)
                i = n if j2 < 0 else j2 + 1
            else:
                del out[k:]
                i = j + 2
            continue
        if css[i:i + 4].lower() == 'url(':
            j = css.find(')', i)
            if j < 0:
                raise Fail('%s 스타일의 url( 이 닫히지 않았습니다' % what)
            out.append(css[i:j + 1])        # 따옴표 없는 url(…) 안의 /* 나 ' 는 주석·문자열이 아니다
            i = j + 1
            continue
        if c in '"\'':
            j = i + 1
            while j < n and css[j] != c:
                if css[j] == '\\':
                    j += 1
                j += 1
            if j >= n:
                raise Fail('%s 스타일의 문자열이 닫히지 않았습니다' % what)
            out.append(css[i:j + 1])
            i = j + 1
            continue
        out.append(c)
        i += 1
    return ''.join(out)


def strip_code_comments(doc):
    """<script>(인라인) · <style> 안의 주석을 뺀다 — 화면엔 안 보이지만 소스에 사내 작업 메모(누가 알려 줬는지 · 옛 판 사정)가 남지 않게."""
    t = doc.tree()
    eds, n_js, n_css = [], 0, 0
    for nd in t.all:
        if nd.es is None:
            continue
        body = doc.text[nd.se:nd.es]
        if nd.tag == 'script' and 'src' not in nd.attrs and (nd.attrs.get('type') or 'text/javascript').lower() in ('text/javascript', 'module', 'application/javascript'):
            new = strip_js_comments(body, doc.name)
            n_js += new != body
        elif nd.tag == 'style':
            new = strip_css_comments(body, doc.name)
            n_css += new != body
        else:
            continue
        if new != body:
            eds.append((nd.se, nd.es, new))
    doc.text = apply_edits(doc.text, eds)
    doc.log.append('코드 주석 뺌 — 스크립트 %d개 · 스타일 %d개' % (n_js, n_css))


def sync_toc(doc):
    """목차(nav.toc)에서 대상이 없어진 링크를 뺀다."""
    t = doc.tree()
    ids = {n.attrs.get('id') for n in t.all if n.attrs.get('id')}
    gone = [n for n in t.all if n.tag == 'a' and (n.attrs.get('href') or '').startswith('#')
            and any(a.tag == 'nav' and 'toc' in a.cls() for a in n.ancestors())
            and n.attrs['href'][1:] not in ids]
    if gone:
        doc.text = apply_edits(doc.text, [eat_blank_line(doc.text, n.s, n.e) + ('',) for n in gone])
    doc.log.append('목차 링크 %d개 뺌(%s)' % (len(gone), ' '.join(n.attrs['href'] for n in gone)))


def renumber(doc):
    """섹션 번호(span.sec-num)를 남은 순서대로 01, 02 … 로."""
    t = doc.tree()
    nums = [n for n in t.all if n.tag == 'span' and 'sec-num' in n.cls()]
    eds = [(n.se, n.es, '%02d' % (i + 1)) for i, n in enumerate(nums)]
    doc.text = apply_edits(doc.text, eds)
    doc.log.append('섹션 번호 %d개 다시 매김' % len(nums))


def head_meta(doc):
    """검색에 안 잡히게(주소를 아는 사람만 연다). 「자동 생성」 주석은 넣지 않는다 — 다른 원본과 생성기 위치를 소스에 알리는 표지가 된다(2026-11-17 검수)."""
    t = doc.tree()
    vp = query(t, sel('meta', attr=('name', 'viewport')))
    if len(vp) != 1:
        raise Fail('viewport meta 가 %d개입니다' % len(vp))
    if query(t, sel('meta', attr=('name', 'robots'))):
        raise Fail('원본에 robots meta 가 이미 있습니다 — 규칙을 다시 볼 것')
    doc.text = apply_edits(doc.text, [(vp[0].e, vp[0].e,
                                       ('\n\n' if '\n' in doc.text[vp[0].e:vp[0].e + 2] else '') + '<meta name="robots" content="noindex, nofollow">')])
    doc.log.append('robots noindex 추가')


PW_LOCK_HEAD = '''<style>
html.pwl body>*:not(#pwl){display:none!important}
#pwl{display:none}
html.pwl #pwl{display:flex;position:fixed;inset:0;align-items:center;justify-content:center;padding:24px;background:var(--bg)}
#pwl .pwl-card{width:min(380px,100%);box-sizing:border-box;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:36px 32px 26px;text-align:center}
#pwl h1{font-size:20px;font-weight:700;margin:0 0 8px;color:var(--ink)}
#pwl p{font-size:13.5px;color:var(--ink-2);margin:0 0 20px;line-height:1.6}
#pwl input{width:100%;box-sizing:border-box;height:44px;padding:0 14px;border-radius:12px;border:1px solid var(--line);background:var(--bg-soft);color:var(--ink);font:600 14px 'JetBrains Mono',monospace;outline:none}
#pwl input:focus{border-color:var(--lime)}
#pwl button{margin-top:12px;width:100%;height:44px;border:0;border-radius:12px;background:var(--lime);color:var(--lime-ink);font:700 14px 'Inter Tight','Pretendard',sans-serif;cursor:pointer}
#pwl button:disabled{opacity:.5;cursor:default}
#pwl .pwl-msg{min-height:20px;margin-top:12px;font-size:12.5px;color:var(--red)}
#pwl .pwl-note{margin-top:4px;font-size:11.5px;color:var(--ink-3)}
</style>
<script>(function(){var v=null;try{v=JSON.parse(localStorage.getItem('bnpg')||'null')}catch(e){}if(!v||!v.t||!(v.exp*1000>Date.now()))document.documentElement.classList.add('pwl')})();</script>'''

PW_LOCK_BODY = '''<div id="pwl"><form class="pwl-card" autocomplete="off"><h1>BannerNode 사용 설명서</h1><p>ADEF에서 받은 패스워드를 입력해 주세요.</p><input type="password" placeholder="BNP-" spellcheck="false" aria-label="패스워드"><button type="submit">열기</button><div class="pwl-msg" role="alert"></div><div class="pwl-note">이 브라우저에서는 30일 동안 다시 묻지 않아요.</div></form></div>
<script>(function(){
var API='%s',K='bnpg',H=document.documentElement;
var f=document.querySelector('#pwl form'),inp=f.querySelector('input'),btn=f.querySelector('button'),msg=f.querySelector('.pwl-msg');
function get(){try{return JSON.parse(localStorage.getItem(K)||'null')}catch(e){return null}}
function put(v){try{if(v)localStorage.setItem(K,JSON.stringify(v));else localStorage.removeItem(K)}catch(e){}}
var STOP='쓸 수 없는 패스워드예요. ADEF 담당자에게 문의해 주세요.';
var ERR={invalid:'패스워드가 올바르지 않아요.',revoked:STOP,suspended:STOP,rate:'잠시 뒤에 다시 해 주세요.'};
function call(body){return fetch(API,{method:'POST',headers:{'Content-Type':'text/plain;charset=UTF-8'},body:JSON.stringify(body),credentials:'omit',cache:'no-store'}).then(function(r){return r.json().then(function(j){return{s:r.status,j:j||{}}},function(){return{s:r.status,j:{}}})})}
function lock(m){H.classList.add('pwl');msg.textContent=m||'';btn.disabled=false;setTimeout(function(){inp.focus()},0)}
function unlock(){H.classList.remove('pwl');var id=location.hash.slice(1),t=id&&document.getElementById(decodeURIComponent(id));if(t){H.style.scrollBehavior='auto';t.scrollIntoView();H.style.scrollBehavior=''}}
f.addEventListener('submit',function(e){e.preventDefault();var p=inp.value.trim();if(!p){lock('패스워드를 입력해 주세요.');return}
btn.disabled=true;msg.textContent='';
call({password:p}).then(function(r){if(r.s===200&&r.j.ok&&r.j.token){put({t:r.j.token,exp:r.j.exp});inp.value='';btn.disabled=false;unlock()}
else lock(ERR[r.j.error]||(r.s===429?ERR.rate:r.s===403?STOP:r.s>=500?'지금은 확인할 수 없어요. 잠시 뒤에 다시 해 주세요.':ERR.invalid))},function(){lock('연결이 안 돼요. 인터넷 연결을 확인하고 다시 해 주세요.')})});
if(H.classList.contains('pwl')){put(null);setTimeout(function(){inp.focus()},0)}
else call({token:get().t}).then(function(r){if(r.s===401||r.s===403){put(null);lock(r.s===403?STOP:'패스워드를 다시 입력해 주세요.')}},function(){});
})();</script>
''' % GUIDE_API


def pw_lock(doc):
    """패스워드 가리개(2026-11-24 사용자 결정 ①) — 화면을 가릴 뿐 진짜 잠금이 아니다(소스·공개 저장소에는 내용이 있다).
    처음엔 패스워드를 회사 서버(GUIDE_API)에 물어 맞으면 서버가 준 열람 표(30일)를 브라우저에 둔다.
    다음 방문은 표가 있으면 바로 보여 주고 뒤에서 다시 묻는다 — 해지·일시 정지·재발급이면 그때 닫는다. 서버가 안 닿으면 열어 둔 채로 둔다(설명서가 서버 점검에 막히지 않게)."""
    t = doc.tree()
    rb = query(t, sel('meta', attr=('name', 'robots')))
    bd = [n for n in t.all if n.tag == 'body']
    if len(rb) != 1 or len(bd) != 1 or bd[0].es is None:
        raise Fail('가리개 자리(robots meta · body)를 못 찾았습니다')
    if query(t, sel(id='pwl')):
        raise Fail('원본에 #pwl 이 이미 있습니다 — 가리개 id 를 바꿀 것')
    doc.text = apply_edits(doc.text, [(rb[0].e, rb[0].e, '\n' + PW_LOCK_HEAD), (bd[0].es, bd[0].es, PW_LOCK_BODY)])
    doc.log.append('패스워드 가리개 추가(서버 %s)' % GUIDE_API.split('/api/')[1])


# ───────────────────────────── 실행 ─────────────────────────────
def read(p):
    with io.open(p, encoding='utf-8', newline='') as f:
        return f.read()


def build(rules, drules=None):
    src = read(SRC_INDEX)
    doc = Doc(src, 'index.html')
    if '\r\n' in doc.text:
        raise Fail('index.html 이 CRLF 입니다 — 저장소 원본은 LF 입니다. Windows 에서는 받아 둔 사본에서 '
                   '`git config core.autocrlf false` 뒤 파일을 지우고 `git checkout -- index.html workflow-demo.html`')
    rules(doc)
    filter_changelog(doc)
    strip_comments(doc)
    strip_code_comments(doc)
    sync_toc(doc)
    renumber(doc)
    head_meta(doc)
    pw_lock(doc)
    # 데모는 협력사 폴더에 사본을 둔다 — 사내 데모에 사내 전용 장면이 생기면 같은 검사에 걸려 협력사로 넘어가지 않는다
    t = doc.tree()
    fr = [n for n in t.all if n.tag == 'iframe']
    if len(fr) != 1 or not (fr[0].attrs.get('src') or '').startswith('workflow-demo.html'):
        raise Fail('데모 iframe(workflow-demo.html)이 %d개이거나 주소가 바뀌었습니다' % len(fr))
    ddoc = Doc(read(SRC_DEMO).replace('\r\n', '\n'), 'workflow-demo.html')     # 데모는 원래 CRLF — LF 로 맞춰 다룬다(주석을 빼면 줄 끝이 섞인다)
    (drules or demo_rules)(ddoc)
    strip_comments(ddoc)
    strip_code_comments(ddoc)
    head_meta(ddoc)
    demo = ddoc.text
    doc.log += ['데모: ' + x for x in ddoc.log]
    out = {'index.html': doc.text, 'workflow-demo.html': demo}
    doc.log.append('데모 사본 workflow-demo.html(%d바이트)' % len(demo.encode('utf-8')))
    problems = final_gate(doc.text, 'partner/index.html', required_ids=('start',), files=set(out), orig=src)
    problems += final_gate(demo, 'partner/workflow-demo.html', files=set(out))
    return out, doc.log, problems


def write_out(out, outdir):
    os.makedirs(outdir, exist_ok=True)
    wrote = []
    for name, text in out.items():
        p = os.path.join(outdir, name)
        old = read(p) if os.path.exists(p) else None
        if old == text:
            continue
        tmp = p + '.tmp'
        with io.open(tmp, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        os.replace(tmp, p)
        wrote.append(name)
    return wrote


def main(argv, rules):
    global ROOT, SRC_INDEX, SRC_DEMO
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    known, skip = ('--site', '--out', '--check'), False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in ('--site', '--out'):
            skip = True
        elif a not in known:
            print('✗ 모르는 옵션: %s (쓸 수 있는 것: --site <폴더> · --out <폴더> · --check)' % a)
            return 2
    for opt in ('--site', '--out'):
        if opt in argv and (argv.index(opt) + 1 >= len(argv) or argv[argv.index(opt) + 1].startswith('--')):
            print('✗ %s 뒤에 폴더를 적어 주세요.' % opt)
            return 2
    if '--site' in argv:    # 설명서 저장소(받아 둔 사본) 위치를 직접 지정 — 이 파일이 저장소 밖에 있을 때(개발 중)
        ROOT = os.path.abspath(argv[argv.index('--site') + 1])
        SRC_INDEX = os.path.join(ROOT, 'index.html')
        SRC_DEMO = os.path.join(ROOT, 'workflow-demo.html')
    for p in (SRC_INDEX, SRC_DEMO):
        if not os.path.isfile(p):
            print('✗ 설명서 원본을 못 찾았습니다: %s\n  이 파일이 설명서 저장소의 .github/partner/ 안에 있지 않으면 --site <설명서 저장소 사본 폴더> 를 주세요.' % p)
            return 2
    check = '--check' in argv
    outdir = os.path.join(ROOT, 'partner')
    if '--out' in argv:
        outdir = os.path.abspath(argv[argv.index('--out') + 1])
    try:
        out, log, problems = build(rules)
    except Fail as ex:
        print('✗ 생성 실패 — 협력사 페이지는 건드리지 않았습니다.\n  ' + str(ex))
        return 2
    except Exception as ex:     # 예상 밖 오류도 같은 말로 끝낸다(쓰기 전이라 결과는 그대로다)
        import traceback
        traceback.print_exc()
        print('✗ 생성 실패(예상 밖 오류 %s) — 협력사 페이지는 건드리지 않았습니다.' % type(ex).__name__)
        return 2
    for line in log:
        print('  · ' + line)
    if problems:
        print('✗ 최종 검사 실패 %d건 — 협력사 페이지는 건드리지 않았습니다.' % len(problems))
        for p in problems:
            print('  - ' + p)
        return 1
    if check:
        print('✓ 검사 통과(쓰지 않음)')
        return 0
    wrote = write_out(out, outdir)
    print('✓ 검사 통과 · %s' % ('바뀐 파일: ' + ', '.join(wrote) if wrote else '바뀐 것 없음'))
    return 0


# ───────────────────────────── 규칙(사내 설명서 → 협력사 설명서) ─────────────────────────────
def rules(d):
    # ── 1. 로그인 게이트 한 묶음(다섯 곳 = 요소 6개 + CSS) — 게이트 CSS 와 로그인 카드, 또는 게이트 CSS 와 잠금 스크립트만
    #       남으면 페이지가 가려지거나 스크롤이 잠긴다. 나머지는 흔적으로 남는다(최종 검사 GATE_LEFT 가 잡는다) ──
    d.drop(sel('script', attr=('src', 'https://accounts.google.com/gsi/client')), why='구글 로그인 라이브러리')
    d.drop(sel('style', has='#authgate'), why='게이트 CSS(블록 전체가 게이트 전용)')
    d.drop(sel('div', id='authgate'), why='로그인 카드')
    d.drop(sel('script', has='gate-locked'), count=2, why='잠금 스크립트 + 게이트 본체')
    d.drop(sel('button', id='logout'), why='로그아웃 버튼')
    d.css_drop(lambda s: '.theme-btn' in s, why='로그아웃 버튼 CSS')

    # ── 2. NAS 브라우저 장 — 목차 링크와 장 번호는 공통 단계(sync_toc · renumber)가 맞춘다 ──
    d.drop(sel('section', id='nas'), why='NAS 브라우저 장')

    # ── 3. 본문 ──────────────────────────────────────────────────────────────────────────────────────────
    # 쓰는 법(전부 2026-11-10 시운전에서 확인한 것 — README 4절에도 있다)
    #  · 실행 순서: rules(d) → 변경 내역 거르기 → HTML 주석 제거 → 목차 맞춤 → 장 번호 → robots → 데모 → 최종 검사.
    #    규칙이 도는 동안에는 변경 내역 30판 · 주석 · 목차가 아직 있다 → 글자로 고르는 규칙은 반드시 inside=sel('section', id='…') 로 가둔다
    #    (안 가두면 변경 내역의 같은 문구까지 세어 「기대 1곳, 실제 2곳」이 되고, 릴리즈로 변경 내역이 늘 때마다 깨진다).
    #  · 문장 일부만 고칠 때는 d.sub('원문 조각', '고친 조각', inside=…) — 요소의 나머지 글은 사내 설명서를 그대로 따라오고, 조각이 바뀌면 실패한다.
    #    요소를 통째로 갈 때는 d.set_outer(선택자, 새_html, old=규칙을_쓸_때의_원문) — old 를 안 주면 사내 설명서가 그 문단을 고쳐도
    #    실패 없이 옛 협력사 문구가 나간다(「사내 설명서를 올리면 따라온다」가 조용히 깨진다).
    #  · 조사(census)의 replacement 는 「요소 전체(outerHTML)」를 고친 것이고 excerpt 는 그 일부다. d.sub(excerpt, replacement) 로 쓰면
    #    요소가 겹쳐 들어가는데 검사도 통과한다. replacement 에서 바뀐 조각만 떼어 d.sub 로 쓰거나, 요소를 골라 d.set_outer 로 쓴다.
    #  · text= 는 태그 자리에 공백이 들어간 화면 글자(<span class="kbd">Tab</span>으로 → 'Tab 으로'), has= 는 원문 HTML 조각.
    #    둘 다 「가장 안쪽 요소만」 고른다 → tag 와 cls 를 꼭 같이 준다(sel('div', text='…') 는 안쪽 div.label 만 잡아 빈 행이 남는다).
    #  · 기대 횟수는 기본 1. 윈도우·맥 탭에 같은 줄이 두 벌인 #start 는 count=2. count=None 은 「1곳 이상」.
    #  · 그 밖: d.drop · d.unwrap · d.set_inner · d.insert(선택자, html, where='before'|'after'|'prepend'|'append') ·
    #    d.set_attr(선택자, '이름', 값|None) · d.css_drop(lambda 선택자: …) · sel(..., nth=n).
    #    조건 분기는 t = d.tree(); query(t, sel(…)); t.inner(n); ver_tuple(…) 을 그대로 쓴다(예: 다운로드 버전 하한).
    #  · 장 번호 · 목차 링크 · HTML 주석 · 데모 사본은 공통 단계가 맞춘다 — 조사의 그 항목(1133 · 1209 · 1255 · 1313 · 538 · 588 · 주석)은 규칙이 필요 없다.
    #  줄 번호 = 원본 2cf8f1b · 근거 = census 갈래#번호(0부터).

    hero = sel('div', cls='hero')

    def sec(i):
        return sel('section', id=i)

    # 히어로(560 · 568) — ①#1·④#4·⑤#8 / ①#2·④#5·⑤#9 (세 갈래 같은 답)
    d.sub(' 사내 NAS 브라우저도 앱 안에 들어 있어요.</p>', '</p>', inside=hero, why='히어로 소개의 NAS 문장')
    d.drop(sel('span', cls='chip', text='NAS 브라우저', inside=hero), why='히어로 칩')

    # #render(604 · 630 · 632)
    # 604 는 갈래마다 고친 문구가 다르다(①「출력 폴더를 고르거나」 · ②④⑤「폴더 선택 창이 바로 열리고」, ②⑤는 제목도 「출력 폴더 정하기」로).
    #   여기서는 NAS 부분만 빼는 ①#4 를 썼다. 협력사 앱 동작(메뉴 없이 폴더 선택 창이 바로 열림)을 그대로 적으려면 ⑤#11 문구로 바꿀 것.
    d.sub('왼쪽 폴더 버튼으로 <b>로컬 폴더 출력</b> · <b>NAS 폴더 출력</b> 중에 고르거나',
          '왼쪽 폴더 버튼으로 <b>출력 폴더</b>를 고르거나', inside=sec('render'), why='#render 출력 위치 — NAS 폴더 출력(①#4)')
    # 630 — ①#5·②#10 같은 답(⑤#12 는 뒤에 <small>PNG 시퀀스는 그 폴더가 열려요.</small> 를 더 붙인다 — 선택)
    d.sub('만들어진 파일이 열려요. 로컬은 <b>기본 플레이어로 재생</b>, NAS로 뽑았으면 <b>NAS 브라우저</b>가 그 파일을 골라 줍니다.',
          '만들어진 파일이 <b>기본 플레이어로 재생</b>돼요.', inside=sec('render'), why='#render 결과물 바로 열기 — 로컬/NAS 대비 문장')
    # 632 — ①#6·②#11·⑤#13 같은 답(괄호만 뺀다)
    d.sub('(NAS면 <b>NAS 브라우저에서 열기 · 다운로드</b>)', '', inside=sec('render'), why='#render 기록 카드 우클릭 — NAS 괄호')

    # #layout(841~853) — ①#10·④#10·⑤#29
    d.drop(sel('div', cls='card', has='<h3>오른쪽 · NAS 브라우저</h3>', inside=sec('layout')), why='#layout NAS 브라우저 카드')
    # 카드가 4장 → 3장이 되어 2열 격자의 둘째 줄 오른쪽이 빈다(2026-11-17 미리보기에서 확인) → 남은 렌더큐 카드를 두 칸에 걸친다(①#9·④#9)
    _t = d.tree()
    _cards = [n for n in query(_t, sel('div', cls='card', inside=sec('layout'))) if n.parent is not None and 'grid2' in n.parent.cls()]
    _rq = query(_t, sel('div', cls='card', has='<h3>오른쪽 · 렌더큐</h3>', inside=sec('layout')))
    if len(_cards) != 3 or len(_rq) != 1 or _rq[0] is not _cards[-1] or 'style' in _rq[0].attrs:
        raise Fail('#layout 빈칸 보정 — 카드가 %d장이거나 렌더큐 카드가 마지막이 아니거나 style 이 이미 있습니다. 화면을 보고 보정 규칙을 다시 정할 것' % len(_cards))
    d.set_attr(sel('div', cls='card', has='<h3>오른쪽 · 렌더큐</h3>', inside=sec('layout')), 'style', 'grid-column:1 / -1', why='#layout 빈칸 보정(카드 3장)')

    # #import(867 · 879) — ①#11·②#21·④#11·⑤#30 / ①#12·④#12·⑤#31
    d.sub('담는 네 가지 방법.', '담는 세 가지 방법.', inside=sec('import'), why='#import 방법 수(NAS에서 가져오기가 빠져 셋)')
    d.drop(sel('li', text='NAS에서 가져오기', inside=sec('import')), why='#import NAS에서 가져오기(서버 아이콘 svg 포함)')

    # #shortcuts(1161 · 1163 · 1167 · 1175 · 1193)
    d.drop(sel('div', cls='key-row', text='렌더큐 · NAS 전환', inside=sec('shortcuts')), why='단축키 Tab 행(①#16·⑤#34)')
    d.drop(sel('div', cls='key-row', text='NAS 캐시 비우기', inside=sec('shortcuts')), why='단축키 NAS 캐시 비우기 행(①#19·⑤#38) — 「캐시 모두 비우기」 행은 남는다')
    # 1163 — ①#17·②#24 (⑤#35 는 꼬리말이 「고정 · 렌더큐 대기 카드를 하나 골랐을 때」)
    d.sub('이름 바꾸기 / 출력 설정 <small>고정 · NAS 항목 / 렌더큐 대기 카드</small>',
          '출력 설정 <small>고정 · 렌더큐 대기 카드</small>', inside=sec('shortcuts'), why='단축키 F2 — 이름 바꾸기는 NAS 전용')
    # 1167 — ①#18·②#25·⑤#37 같은 답
    d.sub('새로고침 <small>일반: 앱 전체 · NAS 브라우저: 폴더 새로고침</small>',
          '새로고침 <small>앱 전체</small>', inside=sec('shortcuts'), why='단축키 F5 꼬리말')
    # 1193 — ①#20·②#27 (⑤#40 은 「캔버스에서는 노드」 — 「에서는」이 다른 영역이 있다는 느낌을 남겨 ①② 를 골랐다)
    d.sub('<small>캔버스에서는 노드 · NAS 브라우저에서는 NAS 파일</small>',
          '<small>캔버스의 노드</small>', inside=sec('shortcuts'), why='단축키 복사·붙여넣기 꼬리말')

    # #window(1237) — ①#22·⑤#41
    d.drop(sel('li', text='NAS 브라우저를 보는 중이면', inside=sec('window')), why='#window NAS 폴더 새로고침 항목')

    # #start(718 · 747) — ①#7·⑤#19 / ①#8·⑤#24. 윈도우·맥 탭에 같은 줄이 두 벌이라 count=2
    d.drop(sel('li', text='NAS 자동 로그인', inside=sec('start')), count=2, why='#start NAS 자동 로그인 단계(윈도우·맥 탭)')

    # #faq(1265~1271 · 1301) — ①#24·⑤#44 / ①#25·⑤#48(협력사 앱의 실제 라벨은 「저장소」 — 앱 index.html 의 set-sl)
    d.drop(sel('div', cls='card', has='<h3>NAS 파일 이름 바꾸기가 안 돼요.</h3>', inside=sec('faq')), why='#faq NAS 파일 이름 바꾸기 카드')
    d.sub('설정 → <b>NAS · 저장소</b>', '설정 → <b>저장소</b>', inside=sec('faq'), why='#faq 설정 구획 이름')

    # ══ 4. 2026-11-17 사용자 결정 반영(문의처 = 「ADEF 담당자」 · 맥 지원 · 프로젝트 파일 안 주고받음 · 서버 주소 안 씀 ·
    #       「협력사용」 표시 없음 · 페이지 먼저 열고 다운로드는 하한 전까지 「준비 중」) ══

    # ── 다운로드 버전 하한 ─────────────────────────────────────────────────────────────────────────────
    # 협력사 로그인은 앱 v1.0.204(PARTNER_SINCE)부터 있다. 원본이 그보다 낮은 판을 가리키는 동안에는 버튼을 「준비 중」으로 잠근다.
    # 원본 버전이 하한 이상이 되면 아래 분기가 하나도 안 돌아 원본 그대로 나간다(자동으로 풀림).
    # ★ span.ver · span.dl-ver · p.dl-sub · a#dlWin · 다운로드 script 를 고치는 다른 규칙보다 앞에 둘 것(원본 값을 읽는다).
    start = sec('start')
    DL = sel('script', has="const MAC_TAG = '")          # 다운로드 스크립트(원본 1879~1985줄 script)

    t = d.tree()
    _ver = query(t, sel('span', cls='ver'))
    _dlv = query(t, sel('span', cls='dl-ver', inside=start))
    _scr = query(t, DL)
    if len(_ver) != 1 or len(_dlv) != 1 or len(_scr) != 1:
        raise Fail('다운로드 버전 하한 — 버전 표기/스크립트 수가 다릅니다(span.ver %d · span.dl-ver %d · 다운로드 script %d)'
                   % (len(_ver), len(_dlv), len(_scr)))
    v_win = ver_tuple(t.inner(_ver[0]))
    if v_win is None or ver_tuple(t.inner(_dlv[0])) != v_win:
        raise Fail('다운로드 버전 하한 — span.ver(%r)와 span.dl-ver(%r)를 못 읽었거나 서로 다릅니다'
                   % (t.inner(_ver[0]), t.inner(_dlv[0])))
    _js = t.inner(_scr[0])
    _tag = re.findall(r"const\s+MAC_TAG\s*=\s*'([^']*)'\s*;", _js)
    _rdy = re.findall(r"const\s+MAC_READY\s*=\s*(true|false)\s*;", _js)
    if len(_tag) != 1 or len(_rdy) != 1 or ver_tuple(_tag[0]) is None:
        raise Fail('다운로드 버전 하한 — 스크립트의 MAC_TAG(%r) · MAC_READY(%r) 선언을 못 읽었습니다' % (_tag, _rdy))
    win_ok = v_win >= PARTNER_SINCE
    mac_ok = win_ok and ver_tuple(_tag[0]) >= PARTNER_SINCE and _rdy[0] == 'true'
    _since = 'v' + '.'.join(map(str, PARTNER_SINCE))

    if not mac_ok:
        # 맥 버튼은 정적 HTML 이 이미 a.dl-btn.soon(「준비 중」)이다 — 런타임에 되살리는 분기(if(MAC_READY){…})만 끈다
        if _rdy[0] == 'true':
            d.sub('const MAC_READY = true;', 'const MAC_READY = false;', inside=DL,
                  why='다운로드 하한 — 맥 %s < %s: 맥 버튼을 스크립트가 되살리지 않게' % (_tag[0], _since))
        # 맥 접속자에게 받을 수 없는 파일의 설치 안내가 펼쳐지지 않게(dlMacNote 펼침 · dl-sub 맥 문구 교체)
        d.sub("document.getElementById('dlMacNote')", 'null', inside=DL, why='다운로드 하한 — 맥 안내문을 펼치지 않는다')
        d.sub("document.getElementById('dlSubOs')", 'null', inside=DL, why='다운로드 하한 — dl-sub 를 맥 문구로 바꾸지 않는다')
        # 「준비 중」인데 소스에 내려받기 주소가 완성형으로 남지 않게(옛 판 = 패스워드 로그인이 없는 판의 주소다)
        d.sub("const MAC_BASE = 'https://github.com/minsk999/bannernode-guide/releases/download/' + MAC_TAG + '/';", "const MAC_BASE = '';",
              inside=DL, why='다운로드 하한 — 맥 내려받기 주소 상수 비움')

    if not win_ok:
        win = sel('a', id='dlWin', inside=start)
        d.set_attr(win, 'class', 'dl-btn soon', why='다운로드 하한 — Windows 버튼 준비 중(%s < %s)' % (t.inner(_ver[0]), _since))
        d.set_attr(win, 'href', None, why='다운로드 하한 — Windows 링크 제거')
        d.set_attr(win, 'aria-disabled', 'true', why='다운로드 하한 — 원본 맥 버튼(a.dl-btn.soon)과 같은 꼴')
        d.set_attr(win, 'tabindex', '-1', why='다운로드 하한 — 포커스 제외')
        d.sub('<small>.zip</small>', '<small>준비 중</small>', inside=win, why='다운로드 하한 — Windows 버튼 꼬리말')
        # 스크립트가 Windows 버튼에 primary(라임 채움)를 붙이지 않게 — 원본 1913 · 1914줄 두 곳이 모두 win 을 본다
        d.sub("const win = document.getElementById('dlWin');", 'const win = null;', inside=DL,
              why='다운로드 하한 — 준비 중 버튼을 주 버튼으로 강조하지 않는다')
        d.sub(' · 맞는 버튼을 앞에 보여드려요', '', inside=DL, why='다운로드 하한 — 접속 기기 안내 꼬리말(바로 옆 안내와 같은 말이 겹치지 않게 뺀다)')
        d.set_inner(sel('p', cls='dl-sub', inside=start),
                    '다운로드를 준비하고 있어요. 준비되면 이 자리의 버튼이 열립니다 — 아래 설치 안내는 미리 읽어 두셔도 좋아요.',
                    old='무설치 — 압축만 풀면 바로 실행돼요. <span id="dlSubOs">Windows는 <code>BannerNode.exe</code> 더블클릭</span>.',
                    why='다운로드 하한 — 안내 한 줄')
        d.drop(sel('span', cls='dl-ver', inside=start), why='다운로드 하한 — 받을 수 없는 판 번호 알약은 숨긴다(히어로 · 푸터는 그대로)')
        d.sub("const BASE = 'https://github.com/minsk999/bannernode-guide/releases/latest/download/';", "const BASE = '';",
              inside=DL, why='다운로드 하한 — 내려받기 주소 상수 비움')
    else:
        # 열렸을 때: Windows 버튼의 주소를 「latest」가 아니라 그 판 번호로 고정한다 — 사내 설명서의 표기가 릴리즈 게시보다 먼저 올라가도
        # 옛 판(패스워드 로그인이 없는 판)이 내려가지 않는다(릴리즈가 아직 없으면 404 로 끝난다). 2026-11-17 검수.
        _w = query(t, sel('a', id='dlWin', inside=start))
        _href = _w[0].attrs.get('href', '') if len(_w) == 1 else ''
        if _href.count('/releases/latest/download/') != 1:
            raise Fail('다운로드 버전 하한 — a#dlWin 의 주소가 releases/latest/download 꼴이 아닙니다(%r)' % _href[:90])
        d.set_attr(sel('a', id='dlWin', inside=start), 'href',
                   _href.replace('/releases/latest/download/', '/releases/download/%s/' % t.inner(_ver[0]).strip()),
                   why='다운로드 — Windows 주소를 판 번호로 고정(latest 가 옛 판이어도 옛 판이 내려가지 않게)')

    # 끝 확인 — 잠갔다고 한 버튼이 정말 잠겼는가
    if not mac_ok:
        t2 = d.tree()
        _ids = ['dlMacArm', 'dlMacX64'] + ([] if win_ok else ['dlWin'])
        for _i in _ids:
            _b = query(t2, sel('a', id=_i))
            if len(_b) != 1 or 'soon' not in _b[0].cls() or 'href' in _b[0].attrs:
                raise Fail('다운로드 버전 하한 — #%s 가 「준비 중」 꼴이 아닙니다(요소 %d개)' % (_i, len(_b)))
        _s2 = query(t2, DL)
        if len(_s2) != 1 or not re.search(r'const\s+MAC_READY\s*=\s*false\s*;', t2.inner(_s2[0])):
            raise Fail('다운로드 버전 하한 — 스크립트의 MAC_READY 가 false 가 아닙니다')
        if not win_ok and "getElementById('dlWin')" in t2.inner(_s2[0]):
            raise Fail('다운로드 버전 하한 — 스크립트가 아직 Windows 버튼을 잡습니다')
        # 아는 버튼 셋만 잠그면 사내 설명서에 버튼 · 링크가 하나 더 생겼을 때 그대로 살아 나간다 → 다운로드 장 전체로 본다
        _st = query(t2, start)[0]
        for _a in [n for n in t2.all if n.tag == 'a' and _st.s <= n.s < _st.e]:
            _h = _a.attrs.get('href', '')
            _mac = 'macos' in _h.lower() or 'mac' in (_a.attrs.get('id') or '').lower()
            if '/releases/' in _h and (not win_ok or _mac):
                raise Fail('다운로드 버전 하한 — 「준비 중」인데 내려받기 링크가 살아 있습니다(%d줄 %r)' % (t2.line(_a.s), _h[:80]))
            if 'dl-btn' in _a.cls() and (not win_ok or _mac) and ('soon' not in _a.cls() or _h):
                raise Fail('다운로드 버전 하한 — 「준비 중」이 아닌 다운로드 버튼이 있습니다(%d줄 #%s)' % (t2.line(_a.s), _a.attrs.get('id')))
        if '/releases/' in t2.inner(_s2[0]) and not win_ok:
            raise Fail('다운로드 버전 하한 — 스크립트에 내려받기 주소가 남았습니다')
    d.log.append('다운로드 하한 %s — Windows %s(%s) · 맥 %s(%s)' % (_since, '열림' if win_ok else '준비 중', t.inner(_ver[0]).strip(),
                                                              '열림' if mac_ok else '준비 중', _tag[0]))

    # 729줄(⑤#21) — 협력사 앱은 켤 때마다 인터넷으로 패스워드를 확인한다(app.py _gate_ok → _partner_check) → 요구사항에 적는다
    d.sub('<b>시스템 요구사항 — Windows 10/11 · Microsoft Edge WebView2 런타임</b>. 대부분의 PC에는 이미',
          '<b>시스템 요구사항 — Windows 10/11 · Microsoft Edge WebView2 런타임 · 인터넷 연결</b>. WebView2는 대부분의 PC에 이미',
          inside=sec('start'), why='729줄 — 시스템 요구사항에 인터넷 연결')

    # ── 낱말 없는 사내 표현(조사 ②⑤ · 2026-11-17 초안을 원본에서 횟수까지 다시 세어 옮김) ──
    d.sub('영상팀 배너 합성 도구 · 사용 설명서',
          '배너 합성 도구 · 사용 설명서', inside=hero,
          why='556줄 — eyebrow')
    d.sub(('<b>맥도 이제 Windows와 같은 버전이에요.</b> 오랫동안 맥만 v1.0.174 에 머물러 있었는데, 이번 버전부터 두 운영체제가 같은 세대로 함께 올라갑니다 — 그동안 맥에 없던 기능(영상 반복 · 렌더큐 기록 · 크기·배경 변환 등)이 한꺼번에 들어왔어요.<br>\n'
          '            '),
          '', inside=sec('start'), optional=True,
          why='693줄 — 과거 이력 문장(맥만 v1.0.174 에 머물렀다). 릴리즈 공지 글이라 사내 설명서가 스스로 고치거나 뺄 수 있다 → 없으면 넘어간다')
    # 695줄 — 「맥도 지원」(사용자 11-17)인데 「아직 구동 테스트 중 … Windows 버전은 정식」이라 하면 맥 사용자가 써도 되는지 망설인다 → 문의 안내만 남긴다
    d.sub('<b>macOS 버전은 아직 구동 테스트 중이에요.</b> 이상한 점이 있으면 영상팀에 알려주세요 — Windows 버전은 정식입니다.<br>',
          '<b>macOS 버전에서 이상한 점이 보이면</b> ADEF 담당자에게 알려 주세요.<br>', inside=sec('start'),
          why='695줄 — 맥 안내의 「구동 테스트 중」 문장')
    d.sub('<span class="chip dark">Windows</span>', '<span class="chip dark">Windows · macOS</span>', inside=hero,
          why='564줄 — 히어로 칩이 Windows 뿐이라 맥 사용자가 Windows 전용으로 읽는다')
    d.sub('더블클릭하면 앱 창이 뜹니다. 별도 설치 과정은 없어요.</span></li>',
          '더블클릭하면 앱 창이 뜹니다. 별도 설치 과정은 없어요. 보안 경고 창이 먼저 뜨면 아래 <b>Windows 보안</b> 안내대로 열어 주세요.</span></li>',
          inside=sec('start'), why='714줄 — 순서대로 따라 하면 1단계에서 SmartScreen 창을 먼저 만난다')
    d.sub('<b>macOS 14.0(Sonoma) 이상</b>이 필요합니다.</span></div>',
          '<b>macOS 14.0(Sonoma) 이상</b>이 필요하고, 앱을 켤 때마다 <b>인터넷 연결</b>도 필요합니다.</span></div>',
          inside=sec('start'), why='737줄 — 맥 탭에도 인터넷 연결 요구를 적는다')
    # 1283~1285줄 — 옛 판을 써 본 사람에게만 뜻이 있는 질문·답(「클릭해야 반응해요」 「최신 버전에서 … 개선됐어요」)
    d.sub('<h3>앱이 처음에 클릭해야 반응해요 / SmartScreen · 스마트 앱 컨트롤이 막아요.</h3>',
          '<h3>SmartScreen · 스마트 앱 컨트롤이 실행을 막아요.</h3>', inside=sec('faq'), why='1283줄 — FAQ 제목의 옛 판 사정')
    d.sub('최신 버전에서 첫 실행 포커스는 자동으로 잡히도록 개선됐어요. <b>SmartScreen</b>이 막으면',
          '<b>SmartScreen</b>이 막으면', inside=sec('faq'), why='1285줄 — FAQ 답의 옛 판 사정')
    # 1301줄 — 「가져온 사본」이 무엇인지 설명하던 장이 빠졌다 → 한 번 풀어 준다(앱: 끌어다 놓은 파일의 경로를 못 받으면 앱 폴더로 복사한다)
    d.sub('반면 <b>가져온 사본</b>', '반면 <b>가져온 사본</b>(끌어다 놓은 파일을 앱이 따로 복사해 둔 것)', inside=sec('faq'),
          why='1301줄 — 「가져온 사본」 풀이')
    d.sub('사내 배포 앱이라 애플 인증서가 없어서',
          '애플 인증서가 없는 앱이라', count=2, inside=sec('start'),
          why='698줄 — 698줄(다운로드 카드 맥 안내)과 753줄(「처음 한 번 열기」)에 같은 조각이 있어 한 규칙 count=2 로 처리한다')
    d.sub('v1.0.175부터는 앱이 시작할 때 스스로 풀어주므로 그냥 실행하시면 됩니다.',
          '앱이 시작할 때 스스로 풀어 주므로 보통은 그냥 실행하시면 됩니다.', inside=sec('start'),
          why='724줄 — 첫 판이 v1.0.204 라 「v1.0.175부터는」은 뜻이 없는 이력이다')
    d.sub('그 이전 버전에서 이 증상이 났다면, ',
          '그래도 이 창이 뜬다면, ', inside=sec('start'),
          why='725줄 — 「그 이전 버전」은 이 독자에게 없다')
    d.sub('IT에 <b>WebView2 런타임 포함</b>을',
          '회사 IT 담당자에게 <b>WebView2 런타임 포함</b>을', inside=sec('start'),
          why='729줄 — 선택(낮은 우선순위)')
    d.sub('사내 배포용이라 코드 서명이 없어서 뜨는 안내예요. 빌드 직후 첫 실행은',
          '코드 서명이 없는 앱이라 뜨는 안내예요. 새 버전을 처음 실행할 때는', inside=sec('start'),
          why='731줄 — 「사내 배포용」 제거(무서명 사실은 유지)')
    d.sub('쓰지 말고 영상팀에 알려 주세요',
          '쓰지 말고 ADEF 담당자에게 문의해 주세요', inside=sec('start'),
          why='754줄 — 사내 부서 문의 → 결정 ① 꼴')
    d.sub('영상팀이나 IT 담당자에게',
          '회사 IT 담당자나 ADEF 담당자에게', count=2, inside=sec('start'),
          why='756줄 — 756줄·774줄 두 곳(한 규칙 count=2)')
    d.sub('전부 복사해 영상팀에 보내 주세요',
          '전부 복사해 ADEF 담당자에게 보내 주세요', inside=sec('start'),
          why='776줄 — 사내 부서 문의 → ADEF 담당자')
    d.sub('를 영상팀에 보내 주시면',
          '를 ADEF 담당자에게 보내 주시면', inside=sec('faq'),
          why='1277줄 — 사내 부서 문의 → ADEF 담당자')
    d.sub('(사내 배포용 앱이라 코드 서명이 없습니다)',
          '(코드 서명이 없는 앱이라 뜨는 안내예요)', inside=sec('faq'),
          why='1285줄 — 「사내 배포용」 제거, 무서명 사실 유지')
    d.sub('열지 말고 영상팀에 알려 주세요',
          '열지 말고 ADEF 담당자에게 문의해 주세요', inside=sec('faq'),
          why='1293줄 — 1293줄 세 곳 중 첫째(다른 곳에서 받은 파일).')
    d.sub('영상팀이나 IT 담당자에게',
          '회사 IT 담당자나 ADEF 담당자에게', inside=sec('faq'),
          why='1293줄 — 1293줄 둘째(회사가 관리하는 업무용 Mac)')
    d.sub('쓰지 말고 영상팀에 알려 주세요',
          '쓰지 말고 ADEF 담당자에게 문의해 주세요', inside=sec('faq'),
          why='1293줄 — 1293줄 셋째(그래도 안 열리면)')
    d.sub(' · 영상팀 내부용 · ADEF</footer>',
          ' · ADEF</footer>',
          why='1875줄 — 푸터')
    d.sub(' <small>· v1.0.168</small>',
          '', count=2, inside=sec('import'), optional=True,
          why='887줄 — 「이 판에서 새로 생긴 기능」 꼬리표(없으면 넘어간다)')
    d.sub(' 예전에는 갈라진 한쪽만 인식해 영상이 좁게 들어갔습니다.',
          '', inside=sec('import'), optional=True,
          why='889줄 — 「예전에는…」 이력 문장(없으면 넘어간다)')
    # (넣지 않음) 702줄 자리의 「새 버전 받기」 안내 — 앱이 시작 화면에서 스스로 받게 해 주고, 설정의 업데이트 버튼으로 와도 바로 다운로드 카드가 보인다.
    #   사내 설명서에도 없는 글이라 넣으면 앱 버튼 이름이 바뀔 때마다 따로 고쳐야 한다. 894줄 「ADEF에서 받은 프로젝트」 안내도 넣지 않는다(작업 파일을 주고받지 않는다 — 사용자 11-17).

    # ── 로그인 안내(716 · 745 · 1261) + 새 FAQ 2장 — 앱의 실제 문구를 인용한다(app.py _LOGIN_HTML · _partner_gate_msg · partner_login, index.html 협력사 재확인 알림).
    #    ★앱의 그 문구가 바뀌면 여기도 같이 고친다: 「패스워드로 로그인」 · 「입장」 · BNP- · 「서버에 다시 연결하는 중이에요…」 · 「연결이 안 돼요. ADEF 담당자에게 문의해 주세요.」(켤 때·입장 때 같은 문구) ·
    #      「업데이트 받기」(index.html 시작 화면) · 「패스워드로 다시 입장해 주세요.」 · 「패스워드가 올바르지 않아요.」 · 「쓸 수 없는 패스워드예요. ADEF 담당자에게 문의해 주세요.」(켤 때·입장 때 같은 문구) · 「이 패스워드는 더 이상 쓸 수 없어요.」
    #      (2026-11-23 사용자 승인으로 앱 문구가 바뀌어 인용도 고쳤다 — APP-COPY-9.md 4·5행과 짝 문구)
    #    서버 쪽 숫자(유지 기간 · 미사용 만료 일수)는 쓰지 않는다 — 서버가 아직 없다.
    d.set_outer(sel('li', has='<b>ADEF 구글 로그인</b>', inside=start),
                '<li><span class="t"><b>패스워드로 로그인</b> — 처음 켜면 로그인 화면이 떠요. 가운데 큰 버튼이 아니라 그 아래 작은 글씨 <b>패스워드로 로그인</b>을 누르고, ADEF에서 받은 패스워드(<code>BNP-</code>로 시작해요)를 넣은 뒤 <b>입장</b>을 누르세요. 한 번 들어가면 이 컴퓨터에 로그인이 저장돼 다음부터는 바로 열려요. 다만 앱을 켤 때마다 인터넷으로 패스워드가 유효한지 확인하므로 <b>인터넷 연결이 필요합니다</b>. 패스워드가 없거나 들어가지지 않으면 아래 <b>자주 묻는 질문</b>을 봐 주세요.</span></li>',
                count=2, why='#start 로그인 단계(윈도우·맥 탭) → 패스워드 로그인',
                old='<li><span class="t"><b>ADEF 구글 로그인</b> — 처음 한 번 브라우저가 열리며 구글 로그인을 해요. <b>@adef.co.kr</b> · <b>@wisebirds.com</b> 계정으로 로그인할 수 있고, 이후 180일간 유지됩니다.</span></li>')
    d.set_outer(sel('p', cls='lead', has='구성원 전용이라', inside=sec('faq')),
                '<p class="lead" style="margin-bottom:0">처음 한 번 ADEF에서 받은 패스워드로 로그인해야 해요. 로그인 화면 가운데 큰 버튼이 아니라 그 아래 작은 글씨 <b>패스워드로 로그인</b>을 누르고, <code>BNP-</code>로 시작하는 패스워드를 넣은 뒤 <b>입장</b>을 누르면 됩니다. 한 번 로그인하면 이 컴퓨터에 저장돼 다음부터는 바로 열리고, 앱을 켤 때마다 인터넷으로 패스워드가 유효한지 확인해요. 패스워드를 받지 못했거나 잊었다면 ADEF 담당자(이 설명서 주소와 패스워드를 전해 드린 분)에게 문의해 주세요. 로그아웃은 앱 설정 맨 위 계정 항목의 <b>로그아웃</b> 버튼으로 합니다.</p>',
                why='#faq 「처음 켰더니 로그인하라고 떠요」 답',
                old='<p class="lead" style="margin-bottom:0">BannerNode는 ADEF·계열사 구성원 전용이라 처음 한 번 <b>@adef.co.kr</b> 또는 <b>@wisebirds.com</b> 구글 계정으로 로그인해야 해요. 버튼을 누르면 브라우저가 열리고, 로그인하면 180일간 유지됩니다. 계정이 삭제·정지되면(퇴사 등) 다음 확인 때 자동으로 잠깁니다. 로그아웃은 앱 설정의 <b>계정</b> 항목에서.</p>')
    d.insert(sel('div', cls='card', has='<h3>처음 켰더니 로그인하라고 떠요.</h3>', inside=sec('faq')),
             ('\n'
             '\n'
             '        <div class="card">\n'
             '\n'
             '          <h3>켰는데 연결이 안 된다고 떠요.</h3>\n'
             '\n'
             '          <p class="lead" style="margin-bottom:0">BannerNode는 켤 때마다 인터넷으로 패스워드가 유효한지 확인해요. 그 확인이 안 되면 로그인 화면에 <b>“서버에 다시 연결하는 중이에요…”</b>가 뜨고 몇 초 간격으로 스스로 다시 시도합니다 — 잠깐 끊긴 것이라면 그대로 두면 열려요.<br>끝내 안 되면 <b>“연결이 안 돼요. ADEF 담당자에게 문의해 주세요.”</b>로 바뀝니다. 먼저 인터넷 연결을 확인한 뒤 앱을 다시 실행해 주세요. 저장된 로그인은 그대로 남아 있어서 패스워드를 다시 넣을 필요는 없어요.<br>패스워드를 넣고 <b>입장</b>을 눌렀을 때 같은 문구가 뜨면 인터넷 연결을 확인하고 그 자리에서 다시 <b>입장</b>을 눌러 주세요.<br>인터넷이 되는데도 계속 같다면 ADEF 담당자에게 문의해 주세요.</p>\n'
             '\n'
             '        </div>\n'
             '\n'
             '        <div class="card">\n'
             '\n'
             '          <h3>패스워드가 더 이상 안 돼요.</h3>\n'
             '\n'
             '          <p class="lead" style="margin-bottom:0">로그인 화면에 뜨는 문구에 따라 달라요.<br><b>“패스워드로 다시 입장해 주세요.”</b> — 저장돼 있던 로그인이 풀린 것뿐이에요. ADEF에서 가장 최근에 받은 패스워드를 다시 넣으면 됩니다.<br><b>“패스워드가 올바르지 않아요.”</b> — 오타일 가능성이 커요. 맨 앞의 <code>BNP-</code>까지 빠짐없이 넣었는지 확인하고, 받은 글자를 그대로 복사해 붙여 넣어 보세요.<br><b>“쓸 수 없는 패스워드예요. ADEF 담당자에게 문의해 주세요.”</b> — 그 패스워드는 사용이 끝난 거예요. ADEF 담당자에게 문의해 주세요.<br>앱을 쓰는 도중에 <b>“이 패스워드는 더 이상 쓸 수 없어요.”</b> 알림이 뜨면 하던 작업은 그대로 이어서 할 수 있지만 다음 실행부터는 열리지 않아요. 지금 작업을 저장해 두고 ADEF 담당자에게 문의해 주세요.</p>\n'
             '\n'
             '        </div>\n'
             '\n'
             '        <div class="card">\n'
             '\n'
             '          <h3>새 버전은 어떻게 받나요?</h3>\n'
             '\n'
             '          <p class="lead" style="margin-bottom:0">새 버전이 나오면 앱을 켤 때 시작 화면에서 알려 줘요. 거기서 <b>업데이트 받기</b>를 누르면 앱이 직접 내려받고, 다 받은 뒤 화면 안내대로 다시 시작하면 새 버전으로 열립니다. 이 페이지의 다운로드 버튼으로 새로 받아 써도 돼요.</p>\n'
             '\n'
             '        </div>'),
             where='after', why='#faq 새 카드 3장(연결 실패 · 패스워드가 안 될 때 · 새 버전 받기)')


def demo_rules(d):
    """데모 사본(workflow-demo.html) — 동작은 건드리지 않고 사내판 흔적만 뺀다."""
    d.sub('   // 부모(설명서)가 로그인 게이트 해제 순간 호출 — 보는 시점에 1국면부터', '', why='JS 주석 — 로그인 게이트 흔적')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:], rules))
