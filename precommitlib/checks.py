from .lib import BaseCheck, Problem, UsageError


class NoStagedAndUnstagedChanges(BaseCheck):
    """Checks that each staged file doesn't also have unstaged changes."""

    def check(self, fs, repository):
        both = set(repository.staged).intersection(set(repository.unstaged))
        if both:
            message = "\n".join(sorted(both))
            fs.print(message)
            return Problem(autofix=["git", "add"] + list(both))

    def is_fixable(self):
        return True


# We construct it like this so the string literal doesn't trigger the check itself.
DO_NOT_SUBMIT = "DO NOT " + "SUBMIT"


class DoNotSubmit(BaseCheck):
    f"""Checks that files do not contain the string '{DO_NOT_SUBMIT}'."""

    def check(self, fs, repository):
        bad_paths = []
        for path in self.filter(repository.staged):
            with fs.open(path, "rb") as f:
                if DO_NOT_SUBMIT.encode("ascii") in f.read().upper():
                    bad_paths.append(path)

        if bad_paths:
            message = "\n".join(sorted(bad_paths))
            fs.print(message)
            return Problem(f"file contains '{DO_NOT_SUBMIT}'")


class NoWhitespaceInFilePath(BaseCheck):
    """Checks that file paths do not contain whitespace."""

    def check(self, fs, repository):
        bad_paths = []
        for path in self.filter(repository.staged):
            if any(c.isspace() for c in path):
                bad_paths.append(path)

        if bad_paths:
            message = "\n".join(sorted(bad_paths))
            fs.print(message)
            return Problem("file path contains whitespace")


class Command(BaseCheck):
    def __init__(
        self, name, cmd, fix=None, pass_files=False, separately=False, **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name
        self.cmd = cmd
        self.fix = fix

        if separately is True and pass_files is False:
            raise UsageError("if `separately` is True, `pass_files` must also be True")

        self.pass_files = pass_files
        self.separately = separately

    def check(self, fs, repository):
        if self.separately:
            problem = False
            for path in self.filter(repository.staged):
                r = fs.run(self.cmd + [path], capture_output=False)
                if r.returncode != 0:
                    problem = True

            if problem:
                # TODO(2020-04-23): There should be a separate fix command for each
                # file path.
                return Problem(autofix=self.fix)
        else:
            args = self.filter(repository.staged) if self.pass_files else []
            cmd = self.cmd + args
            r = fs.run(cmd, capture_output=False)
            if r.returncode != 0:
                autofix = self.fix + args if self.fix else None
                return Problem(autofix=autofix)

    def get_name(self):
        return self.name

    def is_fixable(self):
        return self.fix is not None


def PythonFormat(args=[], *, include=[], **kwargs):
    return Command(
        "PythonFormat",
        ["black", "--check"] + args,
        pass_files=True,
        include=["*.py"] + include,
        fix=["black"] + args,
        **kwargs,
    )


def PythonLint(args=[], *, include=[], **kwargs):
    return Command(
        "PythonLint",
        ["flake8", "--max-line-length=88"] + args,
        pass_files=True,
        include=["*.py"] + include,
        **kwargs,
    )


def PythonImportOrder(args=[], *, include=[], **kwargs):
    return Command(
        "PythonImportOrder",
        ["isort", "-c"] + args,
        pass_files=True,
        include=["*.py"] + include,
        fix=["isort"] + args,
        **kwargs,
    )


def PythonTypes(args=[], *, include=[], **kwargs):
    return Command(
        "PythonTypes",
        ["mypy"] + args,
        pass_files=True,
        include=["*.py"] + include,
        **kwargs,
    )


def JavaScriptLint(*, include=[], **kwargs):
    return Command(
        "JavaScriptLint",
        ["npx", "eslint"],
        pass_files=True,
        include=["*.js"] + include,
        fix=["npx", "eslint", "--fix"],
        **kwargs,
    )


def RustFormat(args=[], *, include=[], **kwargs):
    return Command(
        "RustFormat",
        ["cargo", "fmt", "--", "--check"] + args,
        pass_files=True,
        include=["*.rs"] + include,
        fix=["cargo", "fmt", "--"] + args,
        **kwargs,
    )
