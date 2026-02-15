from dataclasses import dataclass


@dataclass
class GSOInstance:
    instance_id: str
    repo: str
    base_commit: str
    opt_commit: str
    api: str
    prob_script: str
    tests: list[str]
    hints_text: str
    setup_commands: list[str]
    install_commands: list[str]
    created_at: str
    gt_commit_message: str
    gt_diff: str
    arch: str = "x86_64"
    instance_image_tag: str = "latest"

    @property
    def instance_image_key(self):
        key = (
            f"gso.eval.{self.arch}.{self.instance_id.lower()}:{self.instance_image_tag}"
        )
        return key

    @property
    def remote_instance_image_key(self):
        key = f"slimshetty/gso:gso.eval.{self.arch}.{self.instance_id.lower()}"
        return key

    @property
    def repo_url(self):
        return f"https://github.com/{self.repo}"

    @property
    def install_commands_debug(self):
        if "numpy" in self.repo_url:
            return [
                # "git clean -xfd",
                "uv venv --python 3.11",
                "source .venv/bin/activate",
                "which python",
                "python --version",
                "git submodule update --init",
                # "(uv pip install . --config-settings=setup-args=\"-Dbuildtype=debugoptimized\" --reinstall) || (sed -Ei 's/Cython>=3\\.0(\\.[0-9]+)?/Cython>=3.0,<3.1/I' pyproject.toml && uv pip install . --config-settings=setup-args=\"-Dbuildtype=debugoptimized\" --reinstall) || (git clean -xfd && uv venv --python 3.10 && source .venv/bin/activate && uv pip install \"setuptools<=59.8.0\" \"cython<0.30\" && CFLAGS=\"-g -O2\" CXXFLAGS=\"-g -O2\" uv run python setup.py build_ext --inplace)",
                "(uv pip install . --config-settings=setup-args=\"-Dbuildtype=debugoptimized\" --reinstall) || (sed -Ei 's/Cython>=3\\.0(\\.[0-9]+)?/Cython>=3.0,<3.1/I' pyproject.toml && uv pip install . --config-settings=setup-args=\"-Dbuildtype=debugoptimized\" --reinstall) || (uv venv --python 3.10 && source .venv/bin/activate && uv pip install \"setuptools<=59.8.0\" \"cython<0.30\" && CFLAGS=\"-g -O2\" CXXFLAGS=\"-g -O2\" uv run python setup.py build_ext --inplace)",
                "uv pip install requests dill pillow",
                "uv pip show numpy"
            ]
    
        if "pandas" in self.repo_url:
            return [
                # "git clean -xfd",
                'sed -Ei \'s/"setuptools[^"]*"/"setuptools<82"/\' pyproject.toml',
                "uv venv --python 3.10",
                "source .venv/bin/activate",
                "which python",
                "python --version",
                "uv pip install . --config-settings=setup-args=\"-Dbuildtype=debugoptimized\" --reinstall",
                "uv pip install requests dill \"numpy<2.0\"",
                "uv pip show pandas",
            ]

        if "tokenizers" in self.repo_url:
            return [
                # 'curl -LsSf https://astral.sh/uv/0.5.4/install.sh | sh', 
                'curl https://sh.rustup.rs -sSf | sh -s -- -y && export PATH="$HOME/.cargo/bin:$PATH"', 
                'uv venv --python 3.9', 'source .venv/bin/activate', 
                '. "$HOME/.cargo/env"', 
                'which python', 
                'python --version', 
                'uv pip install "maturin>=1.0,<2.0"', 
                'export RUSTFLAGS="-A invalid_reference_casting -g -C force-frame-pointers=yes"', 
                "export CARGO_PROFILE_RELEASE_DEBUG=2",
                "export CARGO_PROFILE_RELEASE_STRIP=none",
                "export CARGO_PROFILE_RELEASE_SPLIT_DEBUGINFO=off",
                'uv pip install ./bindings/python --reinstall', 
                'uv pip install requests dill datasets==3.5.0 tiktoken scikit-learn', 
                'uv pip show tokenizers'
            ]

        return self.install_commands

    @property
    def install_repo_script(self):
        env_name = "testbed"
        repo_directory = f"/{env_name}"

        # Pin setuptools<82 in build isolation to preserve pkg_resources
        # for legacy setup.py projects (setuptools 82+ removed pkg_resources)
        build_constraint_setup = [
            "echo 'setuptools<82' > /tmp/uv_build_constraints.txt",
            "export UV_BUILD_CONSTRAINT=/tmp/uv_build_constraints.txt",
        ]

        repo_setup = [
            f"git clone -o origin {self.repo_url} {repo_directory}",
            f"chmod -R 777 {repo_directory}",  # nonroot user can run tests
            f"cd {repo_directory}",
            f"git reset --hard {self.base_commit}",
            # Remove remote so agent can't see newer commits
            f"git remote remove origin",
        ]

        repos_with_c = ["numpy", "pandas"]
        for repo in repos_with_c:
            if repo in self.repo_url:
                return (
                    "\n".join(
                        ["#!/bin/bash", "set -euxo pipefail"]
                        + build_constraint_setup
                        + repo_setup
                        + self.install_commands_debug
                    )
                    + "\n"
                )
        return (
            "\n".join(
                ["#!/bin/bash", "set -euxo pipefail"]
                + build_constraint_setup
                + repo_setup
                + self.install_commands
            )
            + "\n"
        )

    @property
    def reset_repo_commands(self):
        return "\n".join(
            [
                f"git remote add origin {self.repo_url}",  # add remote back
                "git fetch origin",  # fetch all branches
                "git clean -xfd",  # clean up untracked files
                "git reset --hard origin/main || git reset --hard origin/master || git reset --hard origin/simd/master",  # reset to main
            ]
        )

    @property
    def platform(self):
        if self.arch == "x86_64":
            return "linux/x86_64"
        elif self.arch == "arm64":
            return "linux/arm64/v8"
        else:
            raise ValueError(f"Invalid architecture: {self.arch}")

    @property
    def test_count(self):
        return len(self.tests)

    def get_instance_container_name(self, run_id=None):
        if not run_id:
            return f"gso.eval.{self.instance_id}"
        return f"gso.eval.{self.instance_id.lower()}.{run_id}"
