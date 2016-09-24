WORK_DIR = $(shell pwd)
WRAPPER = $(shell if [ $(shell echo ${WORK_DIR} | wc -c )  -gt 100 ]; then \
	echo "scripts/wrapper.sh"; \
fi)
VIRTUALENV = $(shell if hash virtualenv2 2>/dev/null; then \
	echo "virtualenv2"; \
else \
	echo "virtualenv"; \
fi)
PYTHON_VERSION = $(lastword $(sort $(wildcard $(addsuffix /python2.?,$(subst :, ,$(PATH))))))
SED_ADVANCED = $(shell if [ "$$(uname -s)" == "Darwin" ]; then echo "sed -E"; else echo "sed -r"; fi)

.PHONY: all build clean complete deps dev install install-cloud jobs-cache organization-deps docs publish-docs python-deps test

install:
	bash scripts/install.sh

all: clean deps build test

build: complete

clean:
	rm -rf build.lib.aeriscloud aeriscloud.egg-info build venv
	rm -f .nodeids .coverage
	rm -f aeriscloud/**/*.pyc

complete:
	$(WRAPPER) venv/bin/aeris $(DEBUG) complete > scripts/complete.sh

deps: python-deps jobs-cache

dev:
	ln -si ../../scripts/pre-commit.sh .git/hooks/pre-commit

install-cloud: deps build

jobs-cache: organization-deps
	@echo "Creating jobs cache ($$($(WRAPPER) venv/bin/aeris-complete path data_dir)/jobs-cache)"
	@(ls "$$($(WRAPPER) venv/bin/aeris-complete path data_dir)"/organizations/*/roles/*/jobs/*.yml 2>/dev/null || echo "") | \
		$(SED_ADVANCED) 's#^.*/organizations/(.*)/roles/(.*\.)?(.*)/jobs/(.*).yml$$#\1/\3/\4#' > \
		$$($(WRAPPER) venv/bin/aeris-complete path data_dir)/jobs-cache

organization-deps:
	$(WRAPPER) venv/bin/cloud -v organization install

docs:
	. venv/bin/activate && cd docs && make html
	hash open 2>/dev/null && open docs/_build/html/index.html || true
	hash xdg-open 2>/dev/null && xdg-open docs/_build/html/index.html || true

publish-docs:
	if ! git diff-index --quiet HEAD; then echo "Repository is dirty, make sure to build docs, commit them then run this command again"; exit 1; fi
	git subtree push --prefix docs/_build/html origin gh-pages

python-deps:
	@if [ -z "$(PYTHON_VERSION)" ]; then echo "error: couldn't find a valid version of python installed"; false; fi
	@if ! hash $(VIRTUALENV) 2>/dev/null; then echo "error: couldn't find a valid version of virtualenv installed"; false; fi
	if [ ! -d venv ]; then $(VIRTUALENV) --python=$(PYTHON_VERSION) venv; fi
	$(WRAPPER) venv/bin/pip install --upgrade pip
	$(WRAPPER) venv/bin/pip install --upgrade -r requirements.txt
	$(WRAPPER) venv/bin/pip install -e .

test:
	AC_NO_ASSISTANT=1 $(WRAPPER) venv/bin/aeris -v test

