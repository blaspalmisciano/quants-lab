.ONESHELL:
.PHONY: uninstall
.PHONY: install

uninstall:
	conda env remove -n quants-lab

install:
	conda env create -f environment.yml
