from prompt_toolkit import CommandLineInterface, AbortAction
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.contrib.shortcuts import create_default_layout
from prompt_toolkit.history import History
from prompt_toolkit.key_binding.manager import KeyBindingManager


class AerisCompletableList(Completer):
    """
    Used to implement an autocompleter that allows selecting
    and un-selecting items, access selected items in self.selected
    """

    def __init__(self, terms, meta_dict=None, allow_selected=False):
        self.terms = list(terms)
        self.meta_dict = meta_dict or {}
        self.selected = []
        self.terms.sort()
        self.allow_selected = allow_selected
        # keep a pristine copy
        self.items = self.terms[:]

    def select(self, term):
        if term not in self.selected:
            self.selected.append(term)
            self.terms.remove(term)

    def unselect(self, term):
        if term in self.selected:
            self.terms.append(term)
            self.selected.remove(term)
            self.terms.sort()

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(True)
        word_len = len(word_before_cursor)

        search_list = self.allow_selected and self.items or self.terms

        if word_before_cursor.startswith('-'):
            word_before_cursor = word_before_cursor[1:]
            word_len -= 1
            search_list = self.selected

        for a in search_list:
            if a.startswith(word_before_cursor):
                display_meta = self.meta_dict.get(a, '')
                yield Completion(a, -word_len,
                                 display_meta=display_meta)


class AerisPrompt(CommandLineInterface):
    """
    Generate an auto-complete prompt using prompt_toolkit
    It is written in pure python and does not depend on readline

    Usage:

    prompt = AerisPrompt('prompt> ')
    input = prompt.get_input()
    """

    def __init__(self, message, completer=None):
        self._completer = completer

        # Create history instance.
        history = History()

        # Load all key bindings.
        manager = KeyBindingManager()

        # Our prompt layout
        layout = create_default_layout(
            message=message,
            reserve_space_for_menu=(completer is not None)
        )

        # Create CLI
        CommandLineInterface.__init__(
            self,
            layout=layout,
            buffer=Buffer(
                history=history,
                completer=completer,
                ),
            key_bindings_registry=manager.registry
        )

    def get_input(self):
        document = self.read_input(on_abort=AbortAction.RETURN_NONE,
                                   on_exit=AbortAction.RETURN_NONE)

        if document:
            return document.text

    def select(self, term):
        self._completer.select(term)

    def unselect(self, term):
        self._completer.unselect(term)
