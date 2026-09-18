# Drift label review — 20 cases (seed 11)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `2a8cd7470bf27f1d`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Improve the contributing guide
- **commit** https://github.com/pallets/flask/commit/34027d8d876c140f84e18d6b56c0aecc5481874c
- **doc** `CONTRIBUTING.rst`
- **no longer asserted after this commit** `help`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/CONTRIBUTING.rst b/CONTRIBUTING.rst
index 3a9177a4..a3c8b851 100644
--- a/CONTRIBUTING.rst
+++ b/CONTRIBUTING.rst
@@ -12,14 +12,16 @@ to address bugs and feature requests in Flask itself. Use one of the
 following resources for questions about using Flask or issues with your
 own code:
 
--   The ``#get-help`` channel on our Discord chat:
+-   The ``#questions`` channel on our Discord chat:
     https://discord.gg/pallets
 -   The mailing list flask@python.org for long term discussion or larger
     issues.
 -   Ask on `Stack Overflow`_. Search with Google first using:
     ``site:stackoverflow.com flask {search term, exception message, etc.}``
+-   Ask on our `GitHub Discussions`_.
 
 .. _Stack Overflow: https://stackoverflow.com/questions/tagged/flask?tab=Frequent
+.. _GitHub Discussions: https://github.com/pallets/flask/discussions
 
 
 Reporting issues
@@ -92,7 +94,7 @@ First time setup
 
     .. code-block:: text
 
-        git remote add fork https://github.com/{username}/flask
+        $ git remote add fork https://github.com/{username}/flask
 
 -   Create a virtualenv.
 

```

</details>

---

## Case 2 — `a6d8321aae66f7f2`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** remove FLASK_ENV from docs
- **commit** https://github.com/pallets/flask/commit/30427a209043bfb9730904e0c34b0dbc40bd21f4
- **doc** `docs/server.rst`
- **no longer asserted after this commit** `development`, `flask_debug`, `flask_env`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/server.rst b/docs/server.rst
index 5c78f171..a34dfab5 100644
--- a/docs/server.rst
+++ b/docs/server.rst
@@ -3,9 +3,9 @@
 Development Server
 ==================
 
-Flask provides a ``run`` command to run the application with a
-development server. In development mode, this server provides an
-interactive debugger and will reload when code is changed.
+Flask provides a ``run`` command to run the application with a development server. In
+debug mode, this server provides an interactive debugger and will reload when code is
+changed.
 
 .. warning::
 
@@ -18,65 +18,18 @@ interactive debugger and will reload when code is changed.
 Command Line
 ------------
 
-The ``flask run`` command line script is the recommended way to run the
-development server. Use the ``--app`` option to point to your
-application, and the ``--env development`` option to fully enable
-development mode.
+The ``flask run`` CLI command is the recommended way to run the development server. Use
+the ``--app`` option to point to your application, and the ``--debug`` option to enable
+debug mode.
 
 .. code-block:: text
 
-    $ flask --app hello --env development run
+    $ flask --app hello --debug run
 
-These options (and any others) can also be set using environment
-variables.
-
-.. tabs::
-
-   .. group-tab:: Bash
-
-      .. code-block:: text
-
-         $ export FLASK_APP=hello
-         $ export FLASK_ENV=development
-         $ flask run
-
-   .. group-tab:: Fish
-
-      .. code-block:: text
-
-         $ set -x FLASK_APP hello
-         $ export FLASK_ENV=development
-         $ flask run
-
-   .. group-tab:: CMD
-
-      .. code-block:: text
-
-         > set FLASK_APP=hello
-         > set FLASK_ENV=development
-         > flask run
-
-   .. group-tab:: Powershell
-
-      .. code-block:: text
-
-         > $env:FLASK_APP = "hello"
-         > $env:FLASK_ENV = "development"
-         > flask run
-
-This enables the development environment, including the interactive
-debugger and reloader, and then starts the server on
-http://localhost:5000/. Use ``flask run --help`` to see the available
-options, and  :doc:`/cli` for detailed instructions about configuring
-and using the CLI.
-
-.. note::
-
-    Debug mode can be controlled separately from the development
-    environment with the ``--debug/--no-debug`` option or the
-    ``FLASK_DEBUG`` environment variable. This is how older versions of
-    Flask worked. You should prefer setting the development environment
-    as shown above.
+This enables debug mode, including the interactive debugger and reloader, and then
+starts the server on http://localhost:5000/. Use ``flask run --help`` to see the
+available options, and :doc:`/cli` for detailed instructions about configuring and using
+the CLI.
 
 
 .. _address-already-in-use:
@@ -144,18 +97,13 @@ while still allowing the server to handle errors on reload.
 In Code
 -------
 
-As an alternative to the ``flask run`` command, the development server
-can also be started from Python with the :meth:`Flask.run` method. This
-method takes arguments similar to the CLI options to control the server.
-The main difference from the CLI command is that the server will crash
-if there are errors when reloading.
-
-``debug=True`` can be passed to enable the debugger and reloader, but
-the ``FLASK_ENV=development`` environment variable is still required to
-fully enable development mode.
+The development server can also be started from Python with the :meth:`Flask.run`
+method. This method takes arguments similar to the CLI options to control the server.
+The main difference from the CLI command is that the server will crash if there are
+errors when reloading. ``debug=True`` can be passed to enable debug mode.
 
-Place the call in a main block, otherwise it will interfere when trying
-to import and run the application with a production server later.
+Place the call in a main block, otherwise it will interfere when trying to import and
+run the app
```

</details>

---

## Case 3 — `ae318ebf82bdea96`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 📝 Update includes in `docs/en/docs/python-types.md` (#12551)
- **commit** https://github.com/fastapi/fastapi/commit/71fcafd13c29fab216a432d4fdfd77555b14483e
- **doc** `docs/en/docs/python-types.md`
- **no longer asserted after this commit** `tutorial009c_py310`, `python_types`, `tutorial009c`, `tutorial001`, `tutorial002`, `tutorial003`, `tutorial004`, `tutorial005`, `tutorial010`, `docs_src`, `python`, `py310`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/python-types.md b/docs/en/docs/python-types.md
index ee192d8cb..6c28577cc 100644
--- a/docs/en/docs/python-types.md
+++ b/docs/en/docs/python-types.md
@@ -22,9 +22,7 @@ If you are a Python expert, and you already know everything about type hints, sk
 
 Let's start with a simple example:
 
-```Python
-{!../../docs_src/python_types/tutorial001.py!}
-```
+{* ../../docs_src/python_types/tutorial001.py *}
 
 Calling this program outputs:
 
@@ -38,9 +36,7 @@ The function does the following:
 * Converts the first letter of each one to upper case with `title()`.
 * <abbr title="Puts them together, as one. With the contents of one after the other.">Concatenates</abbr> them with a space in the middle.
 
-```Python hl_lines="2"
-{!../../docs_src/python_types/tutorial001.py!}
-```
+{* ../../docs_src/python_types/tutorial001.py hl[2] *}
 
 ### Edit it
 
@@ -82,9 +78,7 @@ That's it.
 
 Those are the "type hints":
 
-```Python hl_lines="1"
-{!../../docs_src/python_types/tutorial002.py!}
-```
+{* ../../docs_src/python_types/tutorial002.py hl[1] *}
 
 That is not the same as declaring default values like would be with:
 
@@ -112,9 +106,7 @@ With that, you can scroll, seeing the options, until you find the one that "ring
 
 Check this function, it already has type hints:
 
-```Python hl_lines="1"
-{!../../docs_src/python_types/tutorial003.py!}
-```
+{* ../../docs_src/python_types/tutorial003.py hl[1] *}
 
 Because the editor knows the types of the variables, you don't only get completion, you also get error checks:
 
@@ -122,9 +114,7 @@ Because the editor knows the types of the variables, you don't only get completi
 
 Now you know that you have to fix it, convert `age` to a string with `str(age)`:
 
-```Python hl_lines="2"
-{!../../docs_src/python_types/tutorial004.py!}
-```
+{* ../../docs_src/python_types/tutorial004.py hl[2] *}
 
 ## Declaring types
 
@@ -143,9 +133,7 @@ You can use, for example:
 * `bool`
 * `bytes`
 
-```Python hl_lines="1"
-{!../../docs_src/python_types/tutorial005.py!}
-```
+{* ../../docs_src/python_types/tutorial005.py hl[1] *}
 
 ### Generic types with type parameters
 
@@ -369,9 +357,7 @@ It's just about the words and names. But those words can affect how you and your
 
 As an example, let's take this function:
 
-```Python hl_lines="1  4"
-{!../../docs_src/python_types/tutorial009c.py!}
-```
+{* ../../docs_src/python_types/tutorial009c.py hl[1,4] *}
 
 The parameter `name` is defined as `Optional[str]`, but it is **not optional**, you cannot call the function without the parameter:
 
@@ -387,9 +373,7 @@ say_hi(name=None)  # This works, None is valid 🎉
 
 The good news is, once you are on Python 3.10 you won't have to worry about that, as you will be able to simply use `|` to define unions of types:
 
-```Python hl_lines="1  4"
-{!../../docs_src/python_types/tutorial009c_py310.py!}
-```
+{* ../../docs_src/python_types/tutorial009c_py310.py hl[1,4] *}
 
 And then you won't have to worry about names like `Optional` and `Union`. 😎
 
@@ -451,15 +435,11 @@ You can also declare a class as the type of a variable.
 
 Let's say you have a class `Person`, with a name:
 
-```Python hl_lines="1-3"
-{!../../docs_src/python_types/tutorial010.py!}
-```
+{* ../../docs_src/python_types/tutorial010.py hl[1:3] *}
 
 Then you can declare a variable to be of type `Person`:
 
-```Python hl_lines="6"
-{!../../docs_src/python_types/tutorial010.py!}
-```
+{* ../../docs_src/python_types/tutorial010.py hl[6] *}
 
 And then, again, you get all the editor support:
 

```

</details>

---

## Case 4 — `a71193869db65a47`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 🌐 Sync German docs (#14149)
- **commit** https://github.com/fastapi/fastapi/commit/c6232919292b136bd12ef3e46fb9141c1de1db4e
- **doc** `docs/de/docs/tutorial/dependencies/dependencies-with-yield.md`
- **no longer asserted after this commit** `ver:0.106.0`, `ver:0.110.0`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/de/docs/tutorial/dependencies/dependencies-with-yield.md b/docs/de/docs/tutorial/dependencies/dependencies-with-yield.md
index 178c2673e..e65b073a2 100644
--- a/docs/de/docs/tutorial/dependencies/dependencies-with-yield.md
+++ b/docs/de/docs/tutorial/dependencies/dependencies-with-yield.md
@@ -1,6 +1,6 @@
 # Abhängigkeiten mit `yield` { #dependencies-with-yield }
 
-FastAPI unterstützt Abhängigkeiten, die nach Abschluss einige <abbr title="Manchmal auch genannt „Exit Code“, „Cleanup Code“, „Teardown Code“, „Closing Code“, „Kontext Manager Exit Code“, usw.">zusätzliche Schritte ausführen</abbr>.
+FastAPI unterstützt Abhängigkeiten, die nach Abschluss einige <abbr title="Manchmal auch genannt „Exit Code“, „Cleanup Code“, „Teardown Code“, „Closing Code“, „Kontextmanager Exit Code“, usw.">zusätzliche Schritte ausführen</abbr>.
 
 Verwenden Sie dazu `yield` statt `return` und schreiben Sie die zusätzlichen Schritte / den zusätzlichen Code danach.
 
@@ -35,7 +35,7 @@ Der ge`yield`ete Wert ist das, was in *Pfadoperationen* und andere Abhängigkeit
 
 {* ../../docs_src/dependencies/tutorial007.py hl[4] *}
 
-Der auf die `yield`-Anweisung folgende Code wird ausgeführt, nachdem die Response erstellt wurde, aber bevor sie gesendet wird:
+Der auf die `yield`-Anweisung folgende Code wird nach der Response ausgeführt:
 
 {* ../../docs_src/dependencies/tutorial007.py hl[5:6] *}
 
@@ -51,7 +51,7 @@ Sie können `async`- oder reguläre Funktionen verwenden.
 
 Wenn Sie einen `try`-Block in einer Abhängigkeit mit `yield` verwenden, empfangen Sie alle Exceptions, die bei Verwendung der Abhängigkeit geworfen wurden.
 
-Wenn beispielsweise ein Code irgendwann in der Mitte, in einer anderen Abhängigkeit oder in einer *Pfadoperation*, ein „Rollback“ einer Datenbanktransaktion oder einen anderen Fehler verursacht, empfangen Sie die resultierende Exception in Ihrer Abhängigkeit.
+Wenn beispielsweise ein Code irgendwann in der Mitte, in einer anderen Abhängigkeit oder in einer *Pfadoperation*, ein „Rollback“ einer Datenbanktransaktion macht oder eine andere Exception verursacht, empfangen Sie die Exception in Ihrer Abhängigkeit.
 
 Sie können also mit `except SomeException` diese bestimmte Exception innerhalb der Abhängigkeit handhaben.
 
@@ -95,9 +95,11 @@ Dieses funktioniert dank Pythons <a href="https://docs.python.org/3/library/cont
 
 ## Abhängigkeiten mit `yield` und `HTTPException` { #dependencies-with-yield-and-httpexception }
 
-Sie haben gesehen, dass Ihre Abhängigkeiten `yield` verwenden können und `try`-Blöcke haben können, die Exceptions abfangen.
+Sie haben gesehen, dass Sie Abhängigkeiten mit `yield` verwenden und `try`-Blöcke haben können, die versuchen, irgendeinen Code auszuführen und dann, nach `finally`, Exit-Code ausführen.
 
-Auf die gleiche Weise könnten Sie im Exit-Code nach dem `yield` eine `HTTPException` oder ähnliches auslösen.
+Sie können auch `except` verwenden, um die geworfene Exception abzufangen und damit etwas zu tun.
+
+Zum Beispiel können Sie eine andere Exception auslösen, wie `HTTPException`.
 
 /// tip | Tipp
 
@@ -109,7 +111,7 @@ Aber es ist für Sie da, wenn Sie es brauchen. 🤓
 
 {* ../../docs_src/dependencies/tutorial008b_an_py39.py hl[18:22,31] *}
 
-Eine Alternative zum Abfangen von Exceptions (und möglicherweise auch zum Auslösen einer weiteren `HTTPException`) besteht darin, einen [benutzerdefinierten Exceptionhandler](../handling-errors.md#install-custom-exception-handlers){.internal-link target=_blank} zu erstellen.
+Wenn Sie Exceptions abfangen und darauf basierend eine benutzerdefinierte Response erstellen möchten, erstellen Sie einen [benutzerdefinierten Exceptionhandler](../handling-errors.md#install-custom-exception-handlers){.internal-link target=_blank}.
 
 ## Abhängigkeiten mit `yield` und `except` { #dependencies-with-yield-and-except }
 
@@ -121,7 +123,7 @@ In diesem Fall sieht der Client eine *HTTP 500 Internal Server Error*-Response,
 
 ### In Abhängigkeiten mit `yield` und `exce
```

</details>

---

## Case 5 — `40165ea8e8181f24`

- **repo** `pydantic/pydantic` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Improve docs/usage/exporting_models doc (#6030)
- **commit** https://github.com/pydantic/pydantic/commit/521a1a4eb445742a6ad28ec9bd12075ecfe9737e
- **doc** `docs/usage/exporting_models.md`
- **no longer asserted after this commit** `timedelta_isoformat`, `exclude_defaults`, `models_as_dict`, `exclude_unset`, `skip_defaults`, `dumps_kwargs`, `exclude_none`, `alternative`, `implements`, `references`, `isoformat`, `timedelta`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/exporting_models.md b/docs/usage/exporting_models.md
index 4fe3333ef..5e0aba304 100644
--- a/docs/usage/exporting_models.md
+++ b/docs/usage/exporting_models.md
@@ -5,23 +5,14 @@ and exported in a number of ways:
 
 This is the primary way of converting a model to a dictionary. Sub-models will be recursively converted to dictionaries.
 
-Arguments:
-
-* `include`: fields to include in the returned dictionary; see [below](#advanced-include-and-exclude)
-* `exclude`: fields to exclude from the returned dictionary; see [below](#advanced-include-and-exclude)
-* `by_alias`: whether field aliases should be used as keys in the returned dictionary; default `False`
-* `exclude_unset`: whether fields which were not explicitly set when creating the model should
-  be excluded from the returned dictionary; default `False`.
-  Prior to **v1.0**, `exclude_unset` was known as `skip_defaults`; use of `skip_defaults` is now deprecated
-* `exclude_defaults`: whether fields which are equal to their default values (whether set or otherwise) should
-  be excluded from the returned dictionary; default `False`
-* `exclude_none`: whether fields which are equal to `None` should be excluded from the returned dictionary; default
-  `False`
+See [arguments](../../api/main/#pydantic.main.BaseModel.model_dump) for more information.
 
 Example:
 
 ```py
-from pydantic import BaseModel
+from typing import Any, List, Optional
+
+from pydantic import BaseModel, Field, Json
 
 
 class BarModel(BaseModel):
@@ -29,8 +20,8 @@ class BarModel(BaseModel):
 
 
 class FooBarModel(BaseModel):
-    banana: float
-    foo: str
+    banana: Optional[float] = 1.1
+    foo: str = Field(serialization_alias='foo_alias')
     bar: BarModel
 
 
@@ -43,6 +34,34 @@ print(m.model_dump(include={'foo', 'bar'}))
 #> {'foo': 'hello', 'bar': {'whatever': 123}}
 print(m.model_dump(exclude={'foo', 'bar'}))
 #> {'banana': 3.14}
+print(m.model_dump(by_alias=True))
+#> {'banana': 3.14, 'foo_alias': 'hello', 'bar': {'whatever': 123}}
+print(FooBarModel(foo='hello', bar={'whatever': 123}).model_dump(exclude_unset=True))
+#> {'foo': 'hello', 'bar': {'whatever': 123}}
+print(
+    FooBarModel(banana=1.1, foo='hello', bar={'whatever': 123}).model_dump(
+        exclude_defaults=True
+    )
+)
+#> {'foo': 'hello', 'bar': {'whatever': 123}}
+print(FooBarModel(foo='hello', bar={'whatever': 123}).model_dump(exclude_defaults=True))
+#> {'foo': 'hello', 'bar': {'whatever': 123}}
+print(
+    FooBarModel(banana=None, foo='hello', bar={'whatever': 123}).model_dump(
+        exclude_none=True
+    )
+)
+#> {'foo': 'hello', 'bar': {'whatever': 123}}
+
+
+class Model(BaseModel):
+    x: List[Json[Any]]
+
+
+print(Model(x=['{"a": 1}', '[1, 2]']).model_dump())
+#> {'x': [{'a': 1}, [1, 2]]}
+print(Model(x=['{"a": 1}', '[1, 2]']).model_dump(round_trip=True))
+#> {'x': ['{"a":1}', '[1,2]']}
 ```
 
 ## `dict(model)` and iteration
@@ -78,16 +97,10 @@ for name, value in m:
     #> bar: whatever=123
 ```
 
-## `model.copy(...)`
-
-`copy()` allows models to be duplicated, which is particularly useful for immutable models.
+## `model_copy(...)`
 
-Arguments:
-
-* `include`: fields to include in the returned dictionary; see [below](#advanced-include-and-exclude)
-* `exclude`: fields to exclude from the returned dictionary; see [below](#advanced-include-and-exclude)
-* `update`: a dictionary of values to change when creating the copied model
-* `deep`: whether to make a deep copy of the new model; default `False`
+`model_copy()` allows models to be duplicated, which is particularly useful for immutable models.
+See [arguments](../../api/main/#pydantic.main.BaseModel.model_copy) for more information.
 
 Example:
 
@@ -107,9 +120,6 @@ class FooBarModel(BaseModel):
 
 m = FooBarModel(banana=3.14, foo='hello', bar={'whatever': 123})
 
-# TODO!
-# print(m.model_copy(include={'foo', 'bar'}))
-# print(m.model_copy(exclude={'foo', 'bar'}))
 print(m.model_copy(update={'banana': 0}))
 #> banana=0 foo='hell
```

</details>

---

## Case 6 — `bcf59e01ac35b337`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 📝 Update includes in `docs/fr/docs/tutorial/query-params-str-validations.md` (#12591)
- **commit** https://github.com/fastapi/fastapi/commit/453f559934362cd8372bb5fda0fe550572a2611e
- **doc** `docs/fr/docs/tutorial/query-params-str-validations.md`
- **no longer asserted after this commit** `query_params_str_validations`, `tutorial001`, `tutorial002`, `tutorial003`, `tutorial004`, `tutorial005`, `tutorial006`, `tutorial007`, `tutorial008`, `tutorial009`, `tutorial010`, `tutorial011`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/fr/docs/tutorial/query-params-str-validations.md b/docs/fr/docs/tutorial/query-params-str-validations.md
index b71d1548a..a3cf76302 100644
--- a/docs/fr/docs/tutorial/query-params-str-validations.md
+++ b/docs/fr/docs/tutorial/query-params-str-validations.md
@@ -4,9 +4,7 @@
 
 Commençons avec cette application pour exemple :
 
-```Python hl_lines="9"
-{!../../docs_src/query_params_str_validations/tutorial001.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial001.py hl[9] *}
 
 Le paramètre de requête `q` a pour type `Union[str, None]` (ou `str | None` en Python 3.10), signifiant qu'il est de type `str` mais pourrait aussi être égal à `None`, et bien sûr, la valeur par défaut est `None`, donc **FastAPI** saura qu'il n'est pas requis.
 
@@ -26,17 +24,13 @@ Nous allons imposer que bien que `q` soit un paramètre optionnel, dès qu'il es
 
 Pour cela, importez d'abord `Query` depuis `fastapi` :
 
-```Python hl_lines="3"
-{!../../docs_src/query_params_str_validations/tutorial002.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial002.py hl[3] *}
 
 ## Utiliser `Query` comme valeur par défaut
 
 Construisez ensuite la valeur par défaut de votre paramètre avec `Query`, en choisissant 50 comme `max_length` :
 
-```Python hl_lines="9"
-{!../../docs_src/query_params_str_validations/tutorial002.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial002.py hl[9] *}
 
 Comme nous devons remplacer la valeur par défaut `None` dans la fonction par `Query()`, nous pouvons maintenant définir la valeur par défaut avec le paramètre `Query(default=None)`, il sert le même objectif qui est de définir cette valeur par défaut.
 
@@ -86,17 +80,13 @@ Cela va valider les données, montrer une erreur claire si ces dernières ne son
 
 Vous pouvez aussi rajouter un second paramètre `min_length` :
 
-```Python hl_lines="9"
-{!../../docs_src/query_params_str_validations/tutorial003.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial003.py hl[9] *}
 
 ## Ajouter des validations par expressions régulières
 
 On peut définir une <abbr title="Une expression régulière, regex ou regexp est une suite de caractères qui définit un pattern de correspondance pour les chaînes de caractères.">expression régulière</abbr> à laquelle le paramètre doit correspondre :
 
-```Python hl_lines="10"
-{!../../docs_src/query_params_str_validations/tutorial004.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial004.py hl[10] *}
 
 Cette expression régulière vérifie que la valeur passée comme paramètre :
 
@@ -114,9 +104,7 @@ De la même façon que vous pouvez passer `None` comme premier argument pour l'u
 
 Disons que vous déclarez le paramètre `q` comme ayant une longueur minimale de `3`, et une valeur par défaut étant `"fixedquery"` :
 
-```Python hl_lines="7"
-{!../../docs_src/query_params_str_validations/tutorial005.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial005.py hl[7] *}
 
 /// note | "Rappel"
 
@@ -146,9 +134,7 @@ q: Union[str, None] = Query(default=None, min_length=3)
 
 Donc pour déclarer une valeur comme requise tout en utilisant `Query`, il faut utiliser `...` comme premier argument :
 
-```Python hl_lines="7"
-{!../../docs_src/query_params_str_validations/tutorial006.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial006.py hl[7] *}
 
 /// info
 
@@ -164,9 +150,7 @@ Quand on définit un paramètre de requête explicitement avec `Query` on peut a
 
 Par exemple, pour déclarer un paramètre de requête `q` qui peut apparaître plusieurs fois dans une URL, on écrit :
 
-```Python hl_lines="9"
-{!../../docs_src/query_params_str_validations/tutorial011.py!}
-```
+{* ../../docs_src/query_params_str_validations/tutorial011.py hl[9] *}
 
 Ce qui fait qu'avec une URL comme :
 
@@ -201,9 +185,7 @@ La documentation sera donc mise à jour automatiquement pour autoriser plusieurs
 
 Et l'on peut aussi définir une liste de valeurs par défaut si aucune n'est fournie :
 
-```P
```

</details>

---

## Case 7 — `d2e2b3daf86f0a5b`

- **repo** `encode/httpx` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update index.md
- **commit** https://github.com/encode/httpx/commit/81edb1b45bc3dad3bc5aff7d0a057fb55d4ca30b
- **doc** `docs/index.md`
- **no longer asserted after this commit** `http`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.md b/docs/index.md
index 746ed59..6fd73f3 100644
--- a/docs/index.md
+++ b/docs/index.md
@@ -33,12 +33,12 @@ or trio, and is able to support making large numbers of concurrent requests.
     HTTPX should currently be considered in alpha. We'd love early users and feedback,
     but would strongly recommend pinning your dependencies to the latest median
     release, so that you're able to properly review API changes between package
-    updates. Currently you should be using `http==0.8.*`.
+    updates. Currently you should be using `httpx==0.8.*`.
 
     In particular, the 0.8 release switched HTTPX into focusing exclusively on
     providing an async client, in order to move the project forward, and help
     us [change our approach to providing sync+async support][sync-support]. If
-    you have been using the sync client, you may want to pin to `http==0.7.*`,
+    you have been using the sync client, you may want to pin to `httpx==0.7.*`,
     and wait until our sync client is reintroduced.
 
 ---

```

</details>

---

## Case 8 — `d0a0d56865a9e25c`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Provides a link to the examples src
- **commit** https://github.com/pallets/flask/commit/1b7258f816c2e025acc03a4e775d41a9d4477850
- **doc** `docs/patterns/packages.rst`
- **no longer asserted after this commit** `largerapp`, `examples`, `flask`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/patterns/packages.rst b/docs/patterns/packages.rst
index d1780ca8..1bb84f8c 100644
--- a/docs/patterns/packages.rst
+++ b/docs/patterns/packages.rst
@@ -17,6 +17,10 @@ this::
             login.html
             ...
 
+If you find yourself stuck on something, feel free
+to take a look at the source code for this example.
+You'll find `the full src for this example here`_.
+
 Simple Packages
 ---------------
 
@@ -114,10 +118,6 @@ You should then end up with something like that::
                 login.html
                 ...
 
-If you find yourself stuck on something, feel free
-to take a look at the source code for this example.
-You'll find it located under ``flask/examples/largerapp``.
-
 .. admonition:: Circular Imports
 
    Every Python programmer hates them, and yet we just added some:
@@ -134,6 +134,7 @@ You'll find it located under ``flask/examples/largerapp``.
 
 
 .. _working-with-modules:
+.. _the full src for this example here: https://github.com/pallets/flask/tree/master/examples/patterns/largerapp
 
 Working with Blueprints
 -----------------------

```

</details>

---

## Case 9 — `bb2c23121a2ffd94`

- **repo** `encode/httpx` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Fix out-of-date methods on Response API docs (#673)
- **commit** https://github.com/encode/httpx/commit/e30ec8501664a0d24f2643cac984e7079a88832f
- **doc** `docs/api.md`
- **no longer asserted after this commit** `stream_bytes`, `stream_lines`, `stream_text`, `stream_raw`, `stream`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.md b/docs/api.md
index 2dff987..7762c05 100644
--- a/docs/api.md
+++ b/docs/api.md
@@ -63,10 +63,10 @@
 * `def .raise_for_status()` - **None**
 * `def .json()` - **Any**
 * `def .read()` - **bytes**
-* `def .stream_raw()` - **async bytes iterator**
-* `def .stream_bytes()` - **async bytes iterator**
-* `def .stream_text()` - **async text iterator**
-* `def .stream_lines()` - **async text iterator**
+* `def .aiter_raw()` - **async bytes iterator**
+* `def .aiter_bytes()` - **async bytes iterator**
+* `def .aiter_text()` - **async text iterator**
+* `def .aiter_lines()` - **async text iterator**
 * `def .close()` - **None**
 * `def .next()` - **Response**
 

```

</details>

---

## Case 10 — `ce402391579b74a8`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 📝 Update includes in `docs/en/docs/advanced/events.md` (#12604)
- **commit** https://github.com/fastapi/fastapi/commit/2bd2ccbd1930d58fafe5acb1f2990f5c25b6653a
- **doc** `docs/en/docs/advanced/events.md`
- **no longer asserted after this commit** `tutorial001`, `tutorial002`, `tutorial003`, `docs_src`, `events`, `docs`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/advanced/events.md b/docs/en/docs/advanced/events.md
index efce492f4..19465d891 100644
--- a/docs/en/docs/advanced/events.md
+++ b/docs/en/docs/advanced/events.md
@@ -30,9 +30,7 @@ Let's start with an example and then see it in detail.
 
 We create an async function `lifespan()` with `yield` like this:
 
-```Python hl_lines="16  19"
-{!../../docs_src/events/tutorial003.py!}
-```
+{* ../../docs_src/events/tutorial003.py hl[16,19] *}
 
 Here we are simulating the expensive *startup* operation of loading the model by putting the (fake) model function in the dictionary with machine learning models before the `yield`. This code will be executed **before** the application **starts taking requests**, during the *startup*.
 
@@ -50,9 +48,7 @@ Maybe you need to start a new version, or you just got tired of running it. 🤷
 
 The first thing to notice, is that we are defining an async function with `yield`. This is very similar to Dependencies with `yield`.
 
-```Python hl_lines="14-19"
-{!../../docs_src/events/tutorial003.py!}
-```
+{* ../../docs_src/events/tutorial003.py hl[14:19] *}
 
 The first part of the function, before the `yield`, will be executed **before** the application starts.
 
@@ -64,9 +60,7 @@ If you check, the function is decorated with an `@asynccontextmanager`.
 
 That converts the function into something called an "**async context manager**".
 
-```Python hl_lines="1  13"
-{!../../docs_src/events/tutorial003.py!}
-```
+{* ../../docs_src/events/tutorial003.py hl[1,13] *}
 
 A **context manager** in Python is something that you can use in a `with` statement, for example, `open()` can be used as a context manager:
 
@@ -88,9 +82,7 @@ In our code example above, we don't use it directly, but we pass it to FastAPI f
 
 The `lifespan` parameter of the `FastAPI` app takes an **async context manager**, so we can pass our new `lifespan` async context manager to it.
 
-```Python hl_lines="22"
-{!../../docs_src/events/tutorial003.py!}
-```
+{* ../../docs_src/events/tutorial003.py hl[22] *}
 
 ## Alternative Events (deprecated)
 
@@ -112,9 +104,7 @@ These functions can be declared with `async def` or normal `def`.
 
 To add a function that should be run before the application starts, declare it with the event `"startup"`:
 
-```Python hl_lines="8"
-{!../../docs_src/events/tutorial001.py!}
-```
+{* ../../docs_src/events/tutorial001.py hl[8] *}
 
 In this case, the `startup` event handler function will initialize the items "database" (just a `dict`) with some values.
 
@@ -126,9 +116,7 @@ And your application won't start receiving requests until all the `startup` even
 
 To add a function that should be run when the application is shutting down, declare it with the event `"shutdown"`:
 
-```Python hl_lines="6"
-{!../../docs_src/events/tutorial002.py!}
-```
+{* ../../docs_src/events/tutorial002.py hl[6] *}
 
 Here, the `shutdown` event handler function will write a text line `"Application shutdown"` to a file `log.txt`.
 

```

</details>

---

## Case 11 — `145f894fed4887fe`

- **repo** `pydantic/pydantic` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Add substance to migration guide section on validator decorators (#5438)
- **commit** https://github.com/pydantic/pydantic/commit/ed75dd6998905d7094948db35317307ab916b8aa
- **doc** `docs/migration.md`
- **no longer asserted after this commit** `annotated`, `except`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/migration.md b/docs/migration.md
index 206fe6abd..362d321c1 100644
--- a/docs/migration.md
+++ b/docs/migration.md
@@ -80,15 +80,91 @@ The following config settings have been renamed:
 
 ### Changes to Validators
 
-* Raising a `TypeError` inside a validator no longer produces a `ValidationError`, but just raises the `TypeError` directly.
-  This was necessary to prevent certain common bugs (such as calling functions with invalid signatures) from
-  being unintentionally converted into `ValidationError` and displayed to users.
-  If you really want `TypeError` to be converted to a `ValidationError` you should use a `try: except:` block that will catch it and do the conversion.
-* `each_item` validators are deprecated and should be replaced with a type annotation using `Annotated` to apply a validator
-  or with a validator that operates on all items at the top level.
-* Changes to `@validator`-decorated function signatures.
+Pydantic V2 introduces many new features and improvements to validators.
+Most of these features are only available by using a new set of decorators:
+
+* `@field_validator`, which replaces `@validator`
+* `@model_validator`, which replaces `@root_validator`
+
+The following sections list some general changes and some changes specific to individual decorators.
+
+#### `TypeError` no longer gets converted into a `ValidationError`
+
+Previously raising `TypeError` within a validator function wrapped that error into a `ValidationError` and, in the case of use facing errors like in FastAPI, would display those errors to users.
+This lead to a variety of bugs, for example calling a function with the wrong signature:
+
+```python
+import pytest
+
+from pydantic import BaseModel, field_validator  # or validator
+
+
+class Model(BaseModel):
+    x: int
+
+    @field_validator('x')
+    def val_x(cls, v: int) -> int:
+        return str.lower(v)  # raises a TypeError
+
+
+with pytest.raises(TypeError):
+    Model(x=1)
+```
+
+This applies to all validators.
+
+### `each_item` is deprecated
+
+For `@validator` the argument is still present and functions.
+For `@field_validator` it is not present at all.
+As you migrate from `@validator` to `@field_validator` you will have to replace `each_item=True` with [validators in Annotated metadata](usage/validators.md#generic-validated-collections).
+
+### `@root_validator(skip_on_failure=False)` is no longer allowed
+
+Since this was the default value in V1 you will need to explicitly pass `skip_on_failure=False` for `pre=False` (the default) validators.
+
+### `allow_reuse` is deprecated
+
+Previously Pydantic tracked re-used functions in decorators to help you avoid some common mistakes.
+We did this by comparing the function's fully qualified name (module name + function name).
+That system has been replaced with a system that tracks things at a per-class level, reducing false positives and bringing the behavior more in line with the errors that type checkers and linters give for overriding a method with another in a class definition.
+
+It is highly likely that if you were using `allow_reuse=True` you can simply delete the parameter and things will work as expected.
+
+For `@validator` this argument is still present but does nothing and emits a deprecation warning.
+It is not present on `@field_validator`.
+
+### Changes to `@validator`'s allowed signatures
+
+In V1 functions wrapped by `@validator` could receive keyword arguments with metadata about what was being validated.
+Some of these arguments have been removed:
+
+* `config`: Pydantic V2's config is now a dictionary instead of a class, which means this argument is no longer backwards compatible. If you need to access the configuration you should migrate to `@field_validator` and use `info.config`.
+* `field`: this argument used to be a `ModelField` object, which was a quasi-internal class that no longer exists in Pydantic V2. Most of this information can still be accessed by using the field name
```

</details>

---

## Case 12 — `d2929073ecf6a49f`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** use pip instead of setup.py in fabric command
- **commit** https://github.com/pallets/flask/commit/aa9a994946acf45187cb12506b47433306aa3473
- **doc** `docs/patterns/fabric.rst`
- **no longer asserted after this commit** `local`, `with`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/patterns/fabric.rst b/docs/patterns/fabric.rst
index f6ae0330..3dbf2146 100644
--- a/docs/patterns/fabric.rst
+++ b/docs/patterns/fabric.rst
@@ -43,36 +43,25 @@ virtual environment::
     env.hosts = ['server1.example.com', 'server2.example.com']
 
     def pack():
-        # create a new source distribution as tarball
+        # build the package
         local('python setup.py sdist --formats=gztar', capture=False)
 
     def deploy():
-        # figure out the release name and version
+        # figure out the package name and version
         dist = local('python setup.py --fullname', capture=True).strip()
-        # upload the source tarball to the temporary folder on the server
-        put('dist/%s.tar.gz' % dist, '/tmp/yourapplication.tar.gz')
-        # create a place where we can unzip the tarball, then enter
-        # that directory and unzip it
-        run('mkdir /tmp/yourapplication')
-        with cd('/tmp/yourapplication'):
-            run('tar xzf /tmp/yourapplication.tar.gz')
-            # now setup the package with our virtual environment's
-            # python interpreter
-            run('/var/www/yourapplication/env/bin/python setup.py install')
-        # now that all is set up, delete the folder again
-        run('rm -rf /tmp/yourapplication /tmp/yourapplication.tar.gz')
-        # and finally touch the .wsgi file so that mod_wsgi triggers
-        # a reload of the application
-        run('touch /var/www/yourapplication.wsgi')
+        filename = '%s.tar.gz' % dist
+
+        # upload the package to the temporary folder on the server
+        put('dist/%s' % filename, '/tmp/%s' % filename)
 
-The example above is well documented and should be straightforward.  Here
-a recap of the most common commands fabric provides:
+        # install the package in the application's virtualenv with pip
+        run('/var/www/yourapplication/env/bin/pip install /tmp/%s' % filename)
 
--   `run` - executes a command on a remote server
--   `local` - executes a command on the local machine
--   `put` - uploads a file to the remote server
--   `cd` - changes the directory on the serverside.  This has to be used
-    in combination with the ``with`` statement.
+        # remove the uploaded package
+        run('rm -r /tmp/%s' % filename)
+
+        # touch the .wsgi file to trigger a reload in mod_wsgi
+        run('touch /var/www/yourapplication.wsgi')
 
 Running Fabfiles
 ----------------

```

</details>

---

## Case 13 — `9264ef0ca11f68e3`

- **repo** `encode/httpx` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Documentation for SSL_CERT_FILE and SSL_CERT_DIR (#3579)
- **commit** https://github.com/encode/httpx/commit/652f051feaf1ab2828e1812eb0c48f9046a8b5ce
- **doc** `docs/advanced/ssl.md`
- **no longer asserted after this commit** `create_default_context`, `configured`, `otherwise`, `requests`, `certifi`, `context`, `default`, `environ`, `cafile`, `capath`, `client`, `create`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/advanced/ssl.md b/docs/advanced/ssl.md
index da40ed2..f61e82c 100644
--- a/docs/advanced/ssl.md
+++ b/docs/advanced/ssl.md
@@ -71,19 +71,7 @@ client = httpx.Client(verify=ctx)
 
 ### Working with `SSL_CERT_FILE` and `SSL_CERT_DIR`
 
-Unlike `requests`, the `httpx` package does not automatically pull in [the environment variables `SSL_CERT_FILE` or `SSL_CERT_DIR`](https://www.openssl.org/docs/manmaster/man3/SSL_CTX_set_default_verify_paths.html). If you want to use these they need to be enabled explicitly.
-
-For example...
-
-```python
-# Use `SSL_CERT_FILE` or `SSL_CERT_DIR` if configured.
-# Otherwise default to certifi.
-ctx = ssl.create_default_context(
-    cafile=os.environ.get("SSL_CERT_FILE", certifi.where()),
-    capath=os.environ.get("SSL_CERT_DIR"),
-)
-client = httpx.Client(verify=ctx)
-```
+`httpx` does respect the `SSL_CERT_FILE` and `SSL_CERT_DIR` environment variables by default. For details, refer to [the section on the environment variables page](../environment_variables.md#ssl_cert_file).
 
 ### Making HTTPS requests to a local server
 

```

</details>

---

## Case 14 — `e61603047f30e76f`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Fix broken cross-references; use :doc: tags where necessary
- **commit** https://github.com/pallets/flask/commit/e771016a5bac3c08987907a2ec63385d58b81be0
- **doc** `docs/deploying/uwsgi.rst`
- **no longer asserted after this commit** `deploying`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/deploying/uwsgi.rst b/docs/deploying/uwsgi.rst
index 50c85fb2..d0501a35 100644
--- a/docs/deploying/uwsgi.rst
+++ b/docs/deploying/uwsgi.rst
@@ -4,13 +4,13 @@ uWSGI
 =====
 
 uWSGI is a deployment option on servers like `nginx`_, `lighttpd`_, and
-`cherokee`_; see :ref:`deploying-fastcgi` and :ref:`deploying-wsgi-standalone`
-for other options.  To use your WSGI application with uWSGI protocol you will
-need a uWSGI server first. uWSGI is both a protocol and an application server;
-the application server can serve uWSGI, FastCGI, and HTTP protocols.
+`cherokee`_; see :doc:`fastcgi` and :doc:`wsgi-standalone` for other options.
+To use your WSGI application with uWSGI protocol you will need a uWSGI server
+first. uWSGI is both a protocol and an application server; the application
+server can serve uWSGI, FastCGI, and HTTP protocols.
 
 The most popular uWSGI server is `uwsgi`_, which we will use for this
-guide.  Make sure to have it installed to follow along.
+guide. Make sure to have it installed to follow along.
 
 .. admonition:: Watch Out
 
@@ -32,13 +32,13 @@ Given a flask application in myapp.py, use the following command:
     $ uwsgi -s /tmp/yourapplication.sock --manage-script-name --mount /yourapplication=myapp:app
 
 The ``--manage-script-name`` will move the handling of ``SCRIPT_NAME`` to uwsgi,
-since its smarter about that. It is used together with the ``--mount`` directive
-which will make requests to ``/yourapplication`` be directed to ``myapp:app``.
-If your application is accessible at root level, you can use a single ``/``
-instead of ``/yourapplication``. ``myapp`` refers to the name of the file of
-your flask application (without extension) or the module which provides ``app``.
-``app`` is the callable inside of your application (usually the line reads
-``app = Flask(__name__)``.
+since it is smarter about that. It is used together with the ``--mount``
+directive which will make requests to ``/yourapplication`` be directed to
+``myapp:app``. If your application is accessible at root level, you can use a
+single ``/`` instead of ``/yourapplication``. ``myapp`` refers to the name of
+the file of your flask application (without extension) or the module which
+provides ``app``. ``app`` is the callable inside of your application (usually
+the line reads ``app = Flask(__name__)``.
 
 If you want to deploy your flask application inside of a virtual environment,
 you need to also add ``--virtualenv /path/to/virtual/environment``. You might

```

</details>

---

## Case 15 — `add88392d2d4aa87`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update windows installation and other notes
- **commit** https://github.com/pallets/flask/commit/a8e88bebd1dff6b982d721c781d87888ef756e4a
- **doc** `docs/installation.rst`
- **no longer asserted after this commit** `distribute_setup`, `easy_install`, `distribute`, `install`, `ver:2.7`, `easy`, `path`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/installation.rst b/docs/installation.rst
index 965e3733..78f192fd 100644
--- a/docs/installation.rst
+++ b/docs/installation.rst
@@ -3,7 +3,7 @@
 Installation
 ============
 
-Flask depends on two external libraries, `Werkzeug
+Flask depends on some external libraries, like `Werkzeug
 <http://werkzeug.pocoo.org/>`_ and `Jinja2 <http://jinja.pocoo.org/2/>`_.
 Werkzeug is a toolkit for WSGI, the standard Python interface between web
 applications and a variety of servers for both development and deployment.
@@ -13,7 +13,7 @@ So how do you get all that on your computer quickly?  There are many ways you
 could do that, but the most kick-ass method is virtualenv, so let's have a look
 at that first.
 
-You will need Python 2.6 or higher to get started, so be sure to have an
+You will need Python 2.6 or newer to get started, so be sure to have an
 up-to-date Python 2.x installation.  For using Flask with Python 3 have a
 look at :ref:`python3-support`.
 
@@ -67,7 +67,7 @@ folder within::
     $ cd myproject
     $ virtualenv venv
     New python executable in venv/bin/python
-    Installing distribute............done.
+    Installing setuptools, pip............done.
 
 Now, whenever you want to work on a project, you only have to activate the
 corresponding environment.  On OS X and Linux, do the following::
@@ -113,9 +113,9 @@ Get the git checkout in a new virtualenv and run in development mode::
     $ git clone http://github.com/mitsuhiko/flask.git
     Initialized empty Git repository in ~/dev/flask/.git/
     $ cd flask
-    $ virtualenv venv --distribute
+    $ virtualenv venv
     New python executable in venv/bin/python
-    Installing distribute............done.
+    Installing setuptools, pip............done.
     $ . venv/bin/activate
     $ python setup.py develop
     ...
@@ -129,45 +129,53 @@ To just get the development version without git, do this instead::
 
     $ mkdir flask
     $ cd flask
-    $ virtualenv venv --distribute
+    $ virtualenv venv
     $ . venv/bin/activate
     New python executable in venv/bin/python
-    Installing distribute............done.
+    Installing setuptools, pip............done.
     $ pip install Flask==dev
     ...
     Finished processing dependencies for Flask==dev
 
 .. _windows-easy-install:
 
-`pip` and `distribute` on Windows
------------------------------------
+`pip` and `setuptools` on Windows
+---------------------------------
+
+Sometimes getting the standard "Python packaging tools" like *pip*, *setuptools*
+and *virtualenv* can be a little trickier, but nothing very hard. The two crucial
+packages you will need are setuptools and pip - these will let you install
+anything else (like virtualenv). Fortunately there are two "bootstrap scripts"
+you can run to install either.
+
+If you don't currently have either, then `get-pip.py` will install both for you
+(you won't need to run ez_setup.py).
+
+`get-pip.py`_
 
-On Windows, installation of `easy_install` is a little bit trickier, but still
-quite easy.  The easiest way to do it is to download the
-`distribute_setup.py`_ file and run it.  The easiest way to run the file is to
-open your downloads folder and double-click on the file.
+To install the latest setuptools, you can use its bootstrap file:
 
-Next, add the `easy_install` command and other Python scripts to the
-command search path, by adding your Python installation's Scripts folder
-to the `PATH` environment variable.  To do that, right-click on the
-"Computer" icon on the Desktop or in the Start menu, and choose "Properties".
-Then click on "Advanced System settings" (in Windows XP, click on the
-"Advanced" tab instead).  Then click on the "Environment variables" button.
-Finally, double-click on the "Path" variable in the "System variables" section,
-and add the path of your Python interpreter's Scripts folder. Be sure to
-delimit it from existing values with a semicolon.  Assuming you are using
-Python 2.7 on the default path, add the follo
```

</details>

---

## Case 16 — `35b44d8ab3619ff1`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 📝 Update docs about discussions questions (#11985)
- **commit** https://github.com/fastapi/fastapi/commit/4ec134426d6c44a2f7d7c532933ae831e2c6be84
- **doc** `docs/en/docs/management-tasks.md`
- **no longer asserted after this commit** `answered`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/management-tasks.md b/docs/en/docs/management-tasks.md
index 2c91cab72..815bad539 100644
--- a/docs/en/docs/management-tasks.md
+++ b/docs/en/docs/management-tasks.md
@@ -280,8 +280,4 @@ Dependabot will create PRs to update dependencies for several things, and those
 
 When a question in GitHub Discussions has been answered, mark the answer by clicking "Mark as answer".
 
-Many of the current Discussion Questions were migrated from old issues. Many have the label `answered`, that means they were answered when they were issues, but now in GitHub Discussions, it's not known what is the actual response from the messages.
-
-You can filter discussions by [`Questions` that are `Unanswered` and have the label `answered`](https://github.com/fastapi/fastapi/discussions/categories/questions?discussions_q=category%3AQuestions+is%3Aopen+label%3Aanswered+is%3Aunanswered).
-
-All of those discussions already have an answer in the conversation, you can find it and mark it with the "Mark as answer" button.
+You can filter discussions by <a href="https://github.com/tiangolo/fastapi/discussions/categories/questions?discussions_q=category:Questions+is:open+is:unanswered" class="external-link" target="_blank">`Questions` that are `Unanswered`</a>.

```

</details>

---

## Case 17 — `b0468b1842c0f87d`

- **repo** `encode/httpx` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update docs to reflect supported python versions (#2338)
- **commit** https://github.com/encode/httpx/commit/5af6123fff096524b33b8f850ae7017ff1c3d9ac
- **doc** `docs/index.md`
- **no longer asserted after this commit** `ver:3.6`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.md b/docs/index.md
index dca5b7c..ec16ce7 100644
--- a/docs/index.md
+++ b/docs/index.md
@@ -145,6 +145,6 @@ To include the optional brotli decoder support, use:
 $ pip install httpx[brotli]
 ```
 
-HTTPX requires Python 3.6+
+HTTPX requires Python 3.7+
 
 [sync-support]: https://github.com/encode/httpx/issues/572

```

</details>

---

## Case 18 — `b0bdbca946282607`

- **repo** `pydantic/pydantic` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Improve Logfire guidance for validation errors (#13710)
- **commit** https://github.com/pydantic/pydantic/commit/efec1bb51c7a95813d85f1ef5543b4225013d20e
- **doc** `docs/integrations/logfire.md`
- **no longer asserted after this commit** `info`, `user`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/integrations/logfire.md b/docs/integrations/logfire.md
index 8c4f3a45a..da812558b 100644
--- a/docs/integrations/logfire.md
+++ b/docs/integrations/logfire.md
@@ -1,18 +1,20 @@
-Pydantic integrates seamlessly with **Pydantic Logfire**, an observability platform built by us on the same belief as our open source library — that the most powerful tools can be easy to use.
+# Pydantic Logfire
 
-## Getting Started
+Find the data behind production `ValidationError`s. Logfire records failed Pydantic validations with
+their structured errors and can keep them inside the surrounding request or job trace, so you can see
+what failed, where the input came from, and whether the same problem keeps happening.
 
-Logfire has an out-of-the-box Pydantic integration that lets you understand the data passing through your Pydantic models and get analytics on validations. For existing Pydantic users, it delivers unparalleled insights into your usage of Pydantic models.
+## Record failed validations
 
-[Getting started](https://pydantic.dev/docs/logfire/get-started/) with Logfire can be done in three simple steps:
+You need a [free Logfire account](https://logfire.pydantic.dev/login) and project. From your project
+directory, install the SDK and sign in:
 
-1. Set up your Logfire account.
-2. Install the Logfire SDK.
-3. Instrument your project.
-
-### Basic Usage
+```bash
+pip install logfire
+logfire auth
+```
 
-Once you've got Logfire set up, you can start using it to monitor your Pydantic models and get insights into your data validation:
+Call `instrument_pydantic()` before defining or importing the models you want to monitor:
 
 ```python {test="skip"}
 from datetime import date
@@ -21,7 +23,8 @@ import logfire
 
 from pydantic import BaseModel
 
-logfire.configure()  # (1)!
+logfire.configure()
+logfire.instrument_pydantic(record='failure')  # (1)!
 
 
 class User(BaseModel):
@@ -30,19 +33,69 @@ class User(BaseModel):
     dob: date
 
 
-user = User(name='Anne', country_code='USA', dob='2000-01-01')
-logfire.info('user processed: {user!r}', user=user)  # (2)!
+User(name='Anne', country_code='USA', dob='not-a-date')  # (2)!
 ```
 
-1. The `logfire.configure()` call is all you need to instrument your project with Logfire.
-2. The `logfire.info()` call logs the `user` object to Logfire, with builtin support for Pydantic models.
+1. Successful validations stay as aggregate metrics. Failed validations create individual warning
+   records with their structured errors.
+2. Run the example and choose or create a Logfire project when prompted. The invalid date produces
+   a warning record in Logfire's Live view.
+
+!!! warning "Review validation data before exporting it"
+    Failed-validation records contain the rejected values from Pydantic's structured errors. Logfire
+    [scrubs common sensitive values](https://pydantic.dev/docs/logfire/instrument/scrubbing/) before
+    export, but Logfire stores every rejected value under the key `input` inside the serialized
+    `errors` attribute, separately from its field path. If those values can contain secrets or personal
+    data, pass `scrubbing=logfire.ScrubbingOptions(extra_patterns=[r'(?:^input$|"input"\s*:)'])` to
+    `logfire.configure()`. The two alternatives tell the scrubber to inspect serialized validation
+    errors and redact every value whose exact key is `input`; neither refers to your model's field
+    names. Alternatively, use `record='metrics'` so individual failures are not exported.
+
+![A failed Pydantic validation recorded in the Logfire live view](../img/logfire-validation-live-view.png)
+
+Open the warning to inspect the rejected values, error type and field path, and any request or job
+trace active when validation ran. For a deeper walkthrough, see
+[Troubleshooting Validation Errors](../errors/troubleshooting.md).
 
-![basic pydantic logfire usage](../img/basic_logfire.png)
+## Choose how much to record
 
-### Pydantic Instrumentation
+The `record` arg
```

</details>

---

## Case 19 — `67633ac67d18dca7`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** rewrite installation docs discuss python version discuss all dependencies prefer python 3 in instructions [ci skip]
- **commit** https://github.com/pallets/flask/commit/1fb43e3be47ab24cc32396e28a6ad3734e9109e9
- **doc** `docs/installation.rst`
- **no longer asserted after this commit** `easy_install`, `win_add2path`, `activating`, `executable`, `installing`, `setuptools`, `currently`, `depending`, `myproject`, `add2path`, `python27`, `python2`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/installation.rst b/docs/installation.rst
index 38094ded..cd869b9a 100644
--- a/docs/installation.rst
+++ b/docs/installation.rst
@@ -3,188 +3,173 @@
 Installation
 ============
 
-Flask depends on some external libraries, like `Werkzeug
-<http://werkzeug.pocoo.org/>`_ and `Jinja2 <http://jinja.pocoo.org/>`_.
-Werkzeug is a toolkit for WSGI, the standard Python interface between web
-applications and a variety of servers for both development and deployment.
-Jinja2 renders templates.
+Python Version
+--------------
 
-So how do you get all that on your computer quickly?  There are many ways you
-could do that, but the most kick-ass method is virtualenv, so let's have a look
-at that first.
+We recommend using the latest version of Python 3. Flask supports Python 3.3
+and newer, Python 2.6 and newer, and PyPy.
 
-You will need Python 2.6 or newer to get started, so be sure to have an
-up-to-date Python 2.x installation.  For using Flask with Python 3 have a
-look at :ref:`python3-support`.
+Dependencies
+------------
 
-.. _virtualenv:
+These distributions will be installed automatically when installing Flask.
 
-virtualenv
-----------
+* `Werkzeug`_ implements WSGI, the standard Python interface between
+  applications and servers.
+* `Jinja`_ is a template language that renders the pages your application
+  serves.
+* `MarkupSafe`_ comes with Jinja. It escapes untrusted input when rendering
+  templates to avoid injection attacks.
+* `ItsDangerous`_ securely signs data to ensure its integrity. This is used
+  to protect Flask's session cookie.
+* `Click`_ is a framework for writing command line applications. It provides
+  the ``flask`` command and allows adding custom management commands.
 
-Virtualenv is probably what you want to use during development, and if you have
-shell access to your production machines, you'll probably want to use it there,
-too.
+.. _Werkzeug: http://werkzeug.pocoo.org/
+.. _Jinja: http://jinja.pocoo.org/
+.. _MarkupSafe: https://pypi.python.org/pypi/MarkupSafe
+.. _ItsDangerous: https://pythonhosted.org/itsdangerous/
+.. _Click: http://click.pocoo.org/
 
-What problem does virtualenv solve?  If you like Python as much as I do,
-chances are you want to use it for other projects besides Flask-based web
-applications.  But the more projects you have, the more likely it is that you
-will be working with different versions of Python itself, or at least different
-versions of Python libraries.  Let's face it: quite often libraries break
-backwards compatibility, and it's unlikely that any serious application will
-have zero dependencies.  So what do you do if two or more of your projects have
-conflicting dependencies?
+Optional dependencies
+~~~~~~~~~~~~~~~~~~~~~
 
-Virtualenv to the rescue!  Virtualenv enables multiple side-by-side
-installations of Python, one for each project.  It doesn't actually install
-separate copies of Python, but it does provide a clever way to keep different
-project environments isolated.  Let's see how virtualenv works.
+These distributions will not be installed automatically. Flask will detect and
+use them if you install them.
 
+* `Blinker`_ provides support for :ref:`signals`.
+* `SimpleJSON`_ is a fast JSON implementation that is compatible with
+  Python's ``json`` module. It is preferred for JSON operations if it is
+  installed.
 
-.. admonition:: A note on python3 and virtualenv
+.. _Blinker: https://pythonhosted.org/blinker/
+.. _SimpleJSON: https://simplejson.readthedocs.io/
 
-    If you are planning on using python3 with the virtualenv, you don't need to
-    install ``virtualenv``. Python3 has built-in support for virtual environments.
+Virtual environments
+--------------------
 
-If you are on Mac OS X or Linux, chances are that the following
-command will work for you::
+Use a virtual environment to manage the dependencies for your project, both in
+development and in production.
 
-    $ sudo pip install virtualenv
+What problem does a vi
```

</details>

---

## Case 20 — `b8f0be9cef35f4bd`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** fixing cross-reference links on API doc page
- **commit** https://github.com/pallets/flask/commit/4141afa22b6a52279098ef39413f97773c1b75bf
- **doc** `docs/api.rst`
- **no longer asserted after this commit** `exception`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index 50c9820d..fb604abf 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -40,24 +40,24 @@ Incoming Request Data
 
    This is a proxy.  See :ref:`notes-on-proxies` for more information.
 
-   The request object is an instance of a :class:`~werkzeug.Request`
+   The request object is an instance of a :class:`~werkzeug.wrappers.Request`
    subclass and provides all of the attributes Werkzeug defines.  This
    just shows a quick overview of the most important ones.
 
    .. attribute:: form
 
-      A :class:`~werkzeug.MultiDict` with the parsed form data from `POST`
+      A :class:`~werkzeug.datastructures.MultiDict` with the parsed form data from `POST`
       or `PUT` requests.  Please keep in mind that file uploads will not
       end up here,  but instead in the :attr:`files` attribute.
 
    .. attribute:: args
 
-      A :class:`~werkzeug.MultiDict` with the parsed contents of the query
+      A :class:`~werkzeug.datastructures.MultiDict` with the parsed contents of the query
       string.  (The part in the URL after the question mark).
 
    .. attribute:: values
 
-      A :class:`~werkzeug.CombinedMultiDict` with the contents of both
+      A :class:`~werkzeug.datastructures.CombinedMultiDict` with the contents of both
       :attr:`form` and :attr:`args`.
 
    .. attribute:: cookies
@@ -79,11 +79,11 @@ Incoming Request Data
 
    .. attribute:: files
 
-      A :class:`~werkzeug.MultiDict` with files uploaded as part of a
+      A :class:`~werkzeug.datastructures.MultiDict` with files uploaded as part of a
       `POST` or `PUT` request.  Each file is stored as
-      :class:`~werkzeug.FileStorage` object.  It basically behaves like a
+      :class:`~werkzeug.datastructures.FileStorage` object.  It basically behaves like a
       standard file object you know from Python, with the difference that
-      it also has a :meth:`~werkzeug.FileStorage.save` function that can
+      it also has a :meth:`~werkzeug.datastructures.FileStorage.save` function that can
       store the file on the filesystem.
 
    .. attribute:: environ
@@ -228,7 +228,7 @@ Useful Functions and Classes
 
 .. function:: abort(code)
 
-   Raises an :exc:`~werkzeug.exception.HTTPException` for the given
+   Raises an :exc:`~werkzeug.exceptions.HTTPException` for the given
    status code.  For example to abort request handling with a page not
    found exception, you would call ``abort(404)``.
 
@@ -308,7 +308,7 @@ Useful Internals
 
 .. data:: _request_ctx_stack
 
-   The internal :class:`~werkzeug.LocalStack` that is used to implement
+   The internal :class:`~werkzeug.local.LocalStack` that is used to implement
    all the context local objects used in Flask.  This is a documented
    instance and can be used by extensions and application code but the
    use is discouraged in general.
@@ -435,7 +435,7 @@ exceptions where it is good to know that this object is an actual proxy:
     :ref:`signals`)
 
 If you need to get access to the underlying object that is proxied, you
-can use the :meth:`~werkzeug.LocalProxy._get_current_object` method::
+can use the :meth:`~werkzeug.local.LocalProxy._get_current_object` method::
 
     app = current_app._get_current_object()
     my_signal.send(app)

```

</details>

---

