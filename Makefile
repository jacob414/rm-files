VENV_DIR := .venv
MY_PYTHON_VERSION := 3.12

$(VENV_DIR)/bin/activate: requirements.txt
	python$(MY_PYTHON_VERSION) -m venv $(VENV_DIR)
	. $(VENV_DIR)/bin/activate; pip install -r requirements.txt

venv: $(VENV_DIR)/bin/activate

clean:
	rm -rf $(VENV_DIR)

.PHONY: venv clean
