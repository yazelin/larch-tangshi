"""極小測試執行器：@test 收集，main() 逐一跑，失敗印出並以退出碼 1 結束。"""
import sys, traceback
TESTS = []
def test(f): TESTS.append(f); return f
def main():
    bad = 0
    for f in TESTS:
        try: f(); print('ok  ', f.__name__)
        except Exception:
            bad += 1; print('FAIL', f.__name__); traceback.print_exc()
    print(f'{len(TESTS) - bad}/{len(TESTS)} 通過')
    sys.exit(1 if bad else 0)
