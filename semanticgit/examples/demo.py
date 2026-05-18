"""Demo: s-git semantic diff in action."""

from sgit.ast_parser import parse_file
from sgit.commit_gen import generate_commit_message
from sgit.diff_engine import compute_delta, format_delta
from sgit.merge_engine import format_merge_result, merge_snapshots

CODE_V1 = '''\
class Service:
    def process(self, data):
        return data

    def validate(self, data):
        return True

def compute_discount(price, rate):
    return price * rate
'''

CODE_V2 = '''\
import logging

class Service:
    def process(self, data, timeout=30):
        """Process with timeout support."""
        return data

    def validate(self, data):
        logging.info("validating %s", data)
        return True

class BillingManager:
    def compute_discount(self, price, rate, tax_rate=0.0):
        return price * rate * (1 - tax_rate)
'''


def demo_diff() -> None:
    print("=" * 60)
    print("SEMANTIC DIFF DEMO")
    print("=" * 60)

    old = parse_file("service.py", source=CODE_V1)
    new = parse_file("service.py", source=CODE_V2)
    delta = compute_delta(old, new)

    print(format_delta(delta))
    print()

    print("AUTO-GENERATED COMMIT MESSAGE:")
    print("-" * 40)
    print(generate_commit_message([delta]))
    print()


def demo_merge() -> None:
    print("=" * 60)
    print("SEMANTIC MERGE DEMO")
    print("=" * 60)

    base_code = '''\
class App:
    def run(self):
        pass

    def stop(self):
        pass
'''

    ours_code = '''\
class App:
    def run(self):
        print("starting")

    def stop(self):
        pass
'''

    theirs_code = '''\
class App:
    def run(self):
        pass

    def stop(self):
        print("stopping")
'''

    base = parse_file("app.py", source=base_code)
    ours = parse_file("app.py", source=ours_code)
    theirs = parse_file("app.py", source=theirs_code)

    result = merge_snapshots(base, ours, theirs)
    print(format_merge_result(result))
    print()


if __name__ == "__main__":
    demo_diff()
    demo_merge()
