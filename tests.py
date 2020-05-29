import unittest
from io import BytesIO, StringIO

from precommitlib import checks, lib, utils


class Test(unittest.TestCase):
    def setUp(self):
        utils.turn_off_colors()
        checklist = lib.Checklist()
        checklist.check(checks.DoNotSubmit())
        checklist.check(checks.NoStagedAndUnstagedChanges())
        checklist.check(checks.NoWhitespaceInFilePath())
        checklist.check(checks.PythonFormat(exclude=["ignoreme.py"]))

        self.mock_console = MockConsole()
        self.mock_fs = MockFilesystem(self.mock_console)
        self.precommit = lib.Precommit(
            checklist._checks,
            console=self.mock_console,
            fs=self.mock_fs,
            check_all=True,
            dry_run=False,
        )

    def test_check_command(self):
        self.precommit.check()

        output = self.mock_console.captured_output.getvalue()
        self.assertEqual(
            output.strip(),
            multiline(
                """
            o--[ DoNotSubmit ]
            |  ignoreme.py
            |  main.py
            o--[ failed! ]

            o--[ NoStagedAndUnstagedChanges ]
            |  main.py
            o--[ failed! ]

            o--[ NoWhitespaceInFilePath ]
            o--[ passed! ]

            o--[ PythonFormat ]
            |  <failed output of black command>
            o--[ failed! ]


            Ran 4 checks. Detected 3 issues. Fix 2 of them with 'precommit fix'.
        """
            ),
        )

    def test_fix_command(self):
        self.precommit.fix()

        output = self.mock_console.captured_output.getvalue()
        self.assertEqual(
            output.strip(),
            multiline(
                """
            o--[ NoStagedAndUnstagedChanges ]
            |  main.py
            o--[ fixed! ]

            o--[ PythonFormat ]
            |  <failed output of black command>
            o--[ fixed! ]


            Ran 2 fixable checks. Detected 2 issues. Fixed 2 of them.
        """
            ),
        )
        self.assertEqual(
            self.mock_fs.commands_run,
            [
                # `git add` to fix the `NoStagedAndUnstagedChanges` check.
                ["git", "add", "main.py"],
                # Running the `PythonFormat` check.
                ["black", "--check", "main.py"],
                # Fixing the `PythonFormat` check.
                ["black", "main.py"],
                # Adding unstaged changes at the end.
                ["git", "add", "main.py", "ignoreme.py"],
            ],
        )


class MockConsole:
    def __init__(self):
        self.captured_output = StringIO()

    def print(self, *args, **kwargs):
        print(*args, file=self.captured_output, **kwargs)


class MockFilesystem(lib.Filesystem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands_run = []

    def get_staged_files(self):
        return ["main.py", "ignoreme.py"]

    def get_staged_for_deletion_files(self):
        return []

    def get_unstaged_files(self):
        return ["main.py"]

    def open(self, *args, **kwargs):
        # We create the bytestring like this so we don't trigger the DoNotSubmit check.
        return BytesIO(b"DO NOT" + b" SUBMIT")

    def run(self, cmd, *, capture_output=True):
        self.commands_run.append(cmd)
        if cmd[0] == "black" and cmd[1] == "--check":
            self.print("<failed output of black command>")
        return FakeCommandResult(returncode=1)


class FakeCommandResult:
    def __init__(self, returncode, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def multiline(s):
    # Can't use textwrap.dedent because it doesn't ignore blank lines.
    leading_ws = 999
    for line in s.splitlines():
        if not line:
            continue

        for i, c in enumerate(line):
            if not c.isspace():
                leading_ws = min(i, leading_ws)
                break

    return ("\n".join(l[leading_ws:] if l else l for l in s.splitlines())).strip()


if __name__ == "__main__":
    unittest.main()
