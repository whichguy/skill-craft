#!/usr/bin/env python3
"""Scratch prototype of the held-out acceptance sets (F5 (a)). Not harness code.

usage: heldout_probe.py battleship|checkers <delivered-repo-copy>
Starts the product only as its own child on an ephemeral port and kills the child's group in a finally.
"""
import json, os, signal, socket, subprocess, sys, time
import urllib.request, urllib.error
from pathlib import Path


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class Server:
    def __init__(self, repo, port=None, env_port=True):
        self.repo, self.port = repo, port or free_port()
        env = dict(os.environ)
        env.pop("PORT", None)
        if env_port:
            env["PORT"] = str(self.port)
        self.proc = subprocess.Popen(["node", "server.js"], cwd=repo, env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

    def wait(self, seconds=10):
        end = time.time() + seconds
        while time.time() < end:
            if self.proc.poll() is not None:
                return False
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.2).close(); return True
            except OSError:
                time.sleep(0.1)
        return False

    def stop(self):
        try:
            os.killpg(self.proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    def base(self):
        return f"http://127.0.0.1:{self.port}"


def call(base, method, path, body=None, raw=None):
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    req = urllib.request.Request(base + path, data=data, method=method, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            blob = r.read()
            ctype = r.headers.get("content-type", "")
            code = r.status
    except urllib.error.HTTPError as e:
        blob, ctype, code = e.read(), e.headers.get("content-type", ""), e.code
    try:
        return code, json.loads(blob or b"{}"), ctype
    except ValueError:
        return code, {"_text": blob.decode("utf8", "replace")[:200]}, ctype


def gid(j):
    for k in ("game", "id", "gameId"):
        if k in j:
            return j[k]
    return None


# --------------------------------------------------------------------------- battleship
def battleship(repo):
    out = []
    srv = Server(repo)
    try:
        if not srv.wait():
            return [("HB0", "stated", False, "server did not listen")]
        b = srv.base()

        def fire(g, r, c, **kw):
            return call(b, "POST", "/api/fire", {"game": g, "row": r, "col": c}, **kw)

        # HB1 title
        code, j, ctype = call(b, "GET", "/")
        page = j.get("_text", "")
        # call truncated text to 200; refetch whole page
        with urllib.request.urlopen(b + "/", timeout=8) as r:
            html = r.read().decode("utf8", "replace")
            ctype = r.headers.get("content-type", "")
        import re
        t = re.search(r"<title>\s*(.*?)\s*</title>", html, re.S | re.I)
        out.append(("HB1-title", "stated", bool(t) and t.group(1).strip() == "Battleship" and "html" in ctype.lower(),
                    t.group(1) if t else "no title"))
        # HB2 distinct ids
        g1 = gid(call(b, "GET", "/api/new")[1]); g2 = gid(call(b, "GET", "/api/new")[1])
        out.append(("HB2-ids", "stated", g1 is not None and g1 != g2, f"{g1} {g2}"))
        # HB3 sweep semantics on a fresh game
        g = gid(call(b, "GET", "/api/new")[1])
        results, over, first_over = [], [], None
        for r in range(10):
            for c in range(10):
                if first_over is not None:
                    break
                code, j, _ = fire(g, r, c)
                results.append(j.get("result")); over.append(j.get("gameOver"))
                if j.get("gameOver") is True:
                    first_over = len(results) - 1
        valid = all(res in ("miss", "hit", "sunk") for res in results)
        sunk = results.count("sunk")
        at_true = first_over is not None and results[first_over] == "sunk"
        before_false = all(o is not True for o in over[:first_over]) if first_over is not None else False
        out.append(("HB3-sweep", "stated", valid and sunk >= 2 and before_false and at_true,
                    f"valid={valid} sunk={sunk} game_over_at_shot={first_over} last_result={results[first_over] if first_over is not None else None}"))
        # HB5 games independent: g (done) vs a fresh one
        g3 = gid(call(b, "GET", "/api/new")[1])
        code, j, _ = fire(g3, 0, 0)
        out.append(("HB5-independent", "stated", j.get("gameOver") in (False, None) and j.get("result") in ("miss", "hit", "sunk"), str(j)[:80]))
        # HB6 unknown id
        code, j, _ = fire("no-such-game", 0, 0)
        alive = call(b, "GET", "/")[0] == 200
        out.append(("HB6-unknown-game", "robustness", 400 <= code < 500 and alive, f"{code} alive={alive}"))
        # HB7 bad coordinates
        bad = []
        for r, c in ((10, 0), (0, 10), (-1, 0), ("a", 1), (1.5, 2), (None, None)):
            code, j, _ = call(b, "POST", "/api/fire", {"game": g3, "row": r, "col": c})
            bad.append(code)
        alive = call(b, "GET", "/")[0] == 200
        out.append(("HB7-bad-coords", "robustness", all(400 <= x < 500 for x in bad) and alive, f"{bad} alive={alive}"))
        # HB8 malformed JSON
        code, j, _ = call(b, "POST", "/api/fire", raw=b"{not json")
        alive = call(b, "GET", "/")[0] == 200
        out.append(("HB8-malformed-json", "robustness", 400 <= code < 500 and alive, f"{code} alive={alive}"))
        # HB9 a miss stays a miss on repeat
        g4 = gid(call(b, "GET", "/api/new")[1])
        miss_cell = None
        for r in range(10):
            for c in range(10):
                code, j, _ = fire(g4, r, c)
                if j.get("result") == "miss":
                    miss_cell = (r, c); break
            if miss_cell: break
        code, j, _ = fire(g4, *miss_cell)
        out.append(("HB9-repeat-miss", "robustness", (400 <= code < 500) or j.get("result") == "miss", f"{code} {j.get('result')}"))
    finally:
        srv.stop()
    out.append(("HB11-default-port", "stated", None, "not run in scratch: port 3000 belongs to the machine owner"))
    return out


# --------------------------------------------------------------------------- checkers
def checkers(repo):
    out = []
    srv = Server(repo)
    try:
        if not srv.wait():
            return [("HC0", "stated", False, "server did not listen")]
        b = srv.base()

        def new():
            return gid(call(b, "GET", "/api/new")[1])

        def mv(g, f, t):
            return call(b, "POST", "/api/move", {"game": g, "from": f, "to": t})[1]

        def shape(j):
            return isinstance(j.get("ok"), bool) and j.get("turn") in ("red", "black") and "winner" in j

        g = new()
        j = mv(g, [5, 0], [4, 1])
        out.append(("HC2-red-first", "stated", j.get("ok") is False and j.get("turn") == "red", str(j)[:90]))
        g = new(); bad = []
        cases = {"non-diagonal": ([2, 1], [2, 2]), "backward": ([2, 1], [1, 0]), "occupied": ([2, 1], [3, 2]),
                 "from-empty": ([4, 1], [5, 2]), "off-board": ([2, 1], [8, 2]), "negative": ([2, 1], [3, -1]), "light-square": ([2, 2], [3, 3])}
        # occupied target: (1,0)->(2,1) is occupied by red itself
        cases["occupied"] = ([1, 0], [2, 1])
        for name, (f, t) in cases.items():
            j = mv(g, f, t)
            bad.append((name, j.get("ok") is False and j.get("turn") == "red" and shape(j)))
        out.append(("HC4-illegal-keeps-turn+shape", "stated", all(x for _, x in bad), ",".join(n for n, x in bad if not x) or "all"))
        g = new()
        a = mv(g, [2, 1], [3, 0]); bb = mv(g, [5, 0], [4, 1]); cc = mv(g, [2, 3], [3, 4])
        out.append(("HC5-alternate", "stated", a.get("ok") is True and a.get("turn") == "black" and bb.get("ok") is True and bb.get("turn") == "red"
                    and cc.get("ok") is True and cc.get("turn") == "black", f"{a.get('turn')} {bb.get('turn')} {cc.get('turn')}"))
        g = new()
        a = mv(g, [2, 1], [3, 2]); bb = mv(g, [5, 4], [4, 3])
        nonjump = mv(g, [2, 3], [3, 4])
        jump = mv(g, [3, 2], [5, 4])
        out.append(("HC6-mandatory-jump", "stated",
                    a.get("ok") is True and bb.get("ok") is True and nonjump.get("ok") is False and nonjump.get("turn") == "red"
                    and jump.get("ok") is True and jump.get("turn") == "black" and jump.get("winner") is None,
                    f"nonjump_ok={nonjump.get('ok')} jump={str(jump)[:70]}"))
        nonjump_b = mv(g, [5, 2], [4, 1])
        recap = mv(g, [6, 5], [4, 3])
        out.append(("HC7-black-must-jump+removal", "stated", nonjump_b.get("ok") is False and recap.get("ok") is True and recap.get("turn") == "red",
                    f"nonjump_ok={nonjump_b.get('ok')} recapture={str(recap)[:70]}"))
        # robustness
        r1 = call(b, "POST", "/api/move", {"game": "nope", "from": [2, 1], "to": [3, 2]})
        r2 = call(b, "POST", "/api/move", raw=b"{oops")
        r3 = call(b, "POST", "/api/move", {"game": new()})
        alive = call(b, "GET", "/")[0] == 200
        out.append(("HC9-bad-input-survives", "robustness", all(x[0] < 500 for x in (r1, r2, r3)) and alive and r1[1].get("ok") is not True,
                    f"{r1[0]} {r2[0]} {r3[0]} alive={alive}"))
    finally:
        srv.stop()
    return out


if __name__ == "__main__":
    kind, repo = sys.argv[1], sys.argv[2]
    rows = {"battleship": battleship, "checkers": checkers}[kind](repo)
    for r in rows:
        print(("PASS" if r[2] else "n/a " if r[2] is None else "FAIL"), r[0], r[1], r[3])
