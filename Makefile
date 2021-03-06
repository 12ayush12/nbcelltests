PYTHON := python
PIP := pip

run:
	${PYTHON} -m nbcelltests.test Untitled.ipynb

testjs: ## Clean and Make js tests
	yarn test

testpy: ## Clean and Make unit tests
	${PYTHON} -m pytest -v nbcelltests/tests --cov=nbcelltests

testpy-forked: ## Python unit tests --forked (not windows!)
	${PYTHON} -m pytest -v --forked nbcelltests/tests

tests: lint ## run the tests
	${PYTHON} -m pytest -v nbcelltests/tests --cov=nbcelltests --junitxml=python_junit.xml --cov-report=xml --cov-branch
	yarn test

lint: ## run linter
	flake8 nbcelltests setup.py
	yarn lint

fix:  ## run autopep8/tslint fix
	autopep8 --in-place -r -a -a nbcelltests/
	./node_modules/.bin/tslint --fix src/*

extest:  ## run example test
	@ ${PYTHON} -m nbcelltests.test Untitled.ipynb

exlint:  ## run example test
	@ ${PYTHON} -m nbcelltests.lint Untitled.ipynb

annotate: ## MyPy type annotation check
	mypy -s nbcelltests

annotate_l: ## MyPy type annotation check - count only
	mypy -s nbcelltests | wc -l

clean: ## clean the repository
	find . -name "__pycache__" | xargs  rm -rf
	find . -name "*.pyc" | xargs rm -rf
	find . -name ".ipynb_checkpoints" | xargs  rm -rf
	rm -rf .coverage coverage cover htmlcov logs build dist *.egg-info lib node_modules
	# make -C ./docs clean

docs:  ## make documentation
	make -C ./docs html
	open ./docs/_build/html/index.html

install:  ## install to site-packages
	${PIP} install .

serverextension: install ## enable serverextension
	jupyter serverextension enable --py nbcelltests

js:  ## build javascript
	yarn
	yarn build

labextension: js ## enable labextension
	jupyter labextension install .

dist: js  ## create dists
	rm -rf dist build
	${PYTHON} setup.py sdist bdist_wheel

publish: dist  ## dist to pypi and npm
	twine check dist/* && twine upload dist/*
	npm publish

verify-install:  ## verify all components are installed and active
	${PYTHON} -c "import nbcelltests"
	jupyter labextension check jupyterlab_celltests
# apparently can't ask serverextension about individual extensions (and it's OK on linux/mac but ok on windows :) )
	${PYTHON} -c "import subprocess,re,sys;  ext=subprocess.check_output(['jupyter','serverextension','list'],stderr=subprocess.STDOUT).decode();  print(ext);  res0=re.search('nbcelltests\.extension.*OK',ext,re.IGNORECASE);  res1=re.search('nbcelltests\.extension.*enabled', ext);  sys.exit(not (res0 and res1))"

# Thanks to Francoise at marmelab.com for this
.DEFAULT_GOAL := help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

print-%:
	@echo '$*=$($*)'

# TODO looks out of date...most if not all targets in here are phony
.PHONY: clean install serverextension labextension test tests help docs dist
