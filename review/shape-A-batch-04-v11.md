# Drift label review — 25 cases (seed 23)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `638045e07f77e5eb`

- **repo** `encode/httpx` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Convert debug logs to trace logs (#500)
- **commit** https://github.com/encode/httpx/commit/07586f97e85e1cdff1280016f1ee2a1e2ae764b5
- **doc** `docs/environment_variables.md`
- **code** `httpx/dispatch/connection.py`
- **shared identifiers** `host`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/environment_variables.md b/docs/environment_variables.md
index 901e2ad..74c2243 100644
--- a/docs/environment_variables.md
+++ b/docs/environment_variables.md
@@ -11,16 +11,14 @@ There are two ways to set `trust_env` to disable environment variables:
 Here is a list of environment variables that HTTPX recognizes
 and what function they serve:
 
-`HTTPX_DEBUG`
------------
+`HTTPX_LOG_LEVEL`
+-----------------
 
-Valid values: `1`, `true`
+Valid values: `debug`, `trace` (case-insensitive)
 
-If this environment variable is set to a valid value then low-level
-details about the execution of HTTP requests will be logged to `stderr`.
+If set to `trace`, then low-level details about the execution of HTTP requests will be logged to `stderr`. This can help you debug issues and see what's exactly being sent over the wire and to which location.
 
-This can help you debug issues and see what's exactly being sent
-over the wire and to which location.
+The `debug` log level is currently ignored, but is planned to issue high-level logs of HTTP requests.
 
 Example:
 
@@ -33,7 +31,7 @@ with httpx.Client() as client:
 ```
 
 ```console
-user@host:~$ HTTPX_DEBUG=1 python test_script.py
+user@host:~$ HTTPX_LOG_LEVEL=trace python test_script.py
 20:54:17.585 - httpx.dispatch.connection_pool - acquire_connection origin=Origin(scheme='https' host='www.google.com' port=443)
 20:54:17.585 - httpx.dispatch.connection_pool - new_connection connection=HTTPConnection(origin=Origin(scheme='https' host='www.google.com' port=443))
 20:54:17.590 - httpx.dispatch.connection - start_connect host='www.google.com' port=443 timeout=TimeoutConfig(timeout=5.0)

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/httpx/dispatch/connection.py b/httpx/dispatch/connection.py
index 6e8cf0d..91feb97 100644
--- a/httpx/dispatch/connection.py
+++ b/httpx/dispatch/connection.py
@@ -84,10 +84,10 @@ class HTTPConnection(AsyncDispatcher):
         else:
             on_release = functools.partial(self.release_func, self)
 
-        logger.debug(f"start_connect host={host!r} port={port!r} timeout={timeout!r}")
+        logger.trace(f"start_connect host={host!r} port={port!r} timeout={timeout!r}")
         stream = await self.backend.open_tcp_stream(host, port, ssl_context, timeout)
         http_version = stream.get_http_version()
-        logger.debug(f"connected http_version={http_version!r}")
+        logger.trace(f"connected http_version={http_version!r}")
 
         if http_version == "HTTP/2":
             self.h2_connection = HTTP2Connection(
@@ -109,7 +109,7 @@ class HTTPConnection(AsyncDispatcher):
         )
 
     async def close(self) -> None:
-        logger.debug("close_connection")
+        logger.trace("close_connection")
         if self.h2_connection is not None:
             await self.h2_connection.close()
         elif self.h11_connection is not None:

```

</details>

---

## Case 2 — `6a5edcfc7aef4c0e`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Allow str as argument to `Discriminator` (#8047)
- **commit** https://github.com/pydantic/pydantic/commit/a9cebd421744557a64437fc6287513a7a24d63fa
- **doc** `docs/errors/usage_errors.md`
- **code** `pydantic/types.py`
- **shared identifiers** `callablediscriminator`, `pydanticusererror`, `discriminator`, `basemodel`, `callable`, `pydantic`, `model`, `union`, `base`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/errors/usage_errors.md b/docs/errors/usage_errors.md
index fbef1aae3..628cfe833 100644
--- a/docs/errors/usage_errors.md
+++ b/docs/errors/usage_errors.md
@@ -367,14 +367,14 @@ assert Model(pet={'pet_type': 'kitten'}).pet.pet_type == 'cat'
 
 ## Callable discriminator case with no tag {#callable-discriminator-no-tag}
 
-This error is raised when a `Union` that uses a `CallableDiscriminator` doesn't have `Tag` annotations for all cases.
+This error is raised when a `Union` that uses a callable `Discriminator` doesn't have `Tag` annotations for all cases.
 
 ```py
 from typing import Union
 
 from typing_extensions import Annotated
 
-from pydantic import BaseModel, CallableDiscriminator, PydanticUserError, Tag
+from pydantic import BaseModel, Discriminator, PydanticUserError, Tag
 
 
 def model_x_discriminator(v):
@@ -390,7 +390,7 @@ try:
     class DiscriminatedModel(BaseModel):
         x: Annotated[
             Union[str, 'DiscriminatedModel'],
-            CallableDiscriminator(model_x_discriminator),
+            Discriminator(model_x_discriminator),
         ]
 
 except PydanticUserError as exc_info:
@@ -402,7 +402,7 @@ try:
     class DiscriminatedModel(BaseModel):
         x: Annotated[
             Union[Annotated[str, Tag('str')], 'DiscriminatedModel'],
-            CallableDiscriminator(model_x_discriminator),
+            Discriminator(model_x_discriminator),
         ]
 
 except PydanticUserError as exc_info:
@@ -414,7 +414,7 @@ try:
     class DiscriminatedModel(BaseModel):
         x: Annotated[
             Union[str, Annotated['DiscriminatedModel', Tag('model')]],
-            CallableDiscriminator(model_x_discriminator),
+            Discriminator(model_x_discriminator),
         ]
 
 except PydanticUserError as exc_info:

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/types.py b/pydantic/types.py
index c3d914bd3..8c47a395e 100644
--- a/pydantic/types.py
+++ b/pydantic/types.py
@@ -102,7 +102,7 @@ __all__ = (
     'GetPydanticSchema',
     'StringConstraints',
     'Tag',
-    'CallableDiscriminator',
+    'Discriminator',
     'JsonValue',
 )
 
@@ -2443,16 +2443,16 @@ class GetPydanticSchema:
 
 @_dataclasses.dataclass(**_internal_dataclass.slots_true, frozen=True)
 class Tag:
-    """Provides a way to specify the expected tag to use for a case with a callable discriminated union.
+    """Provides a way to specify the expected tag to use for a case of a (callable) discriminated union.
 
     Also provides a way to label a union case in error messages.
 
-    When using a `CallableDiscriminator`, attach a `Tag` to each case in the `Union` to specify the tag that
+    When using a callable `Discriminator`, attach a `Tag` to each case in the `Union` to specify the tag that
     should be used to identify that case. For example, in the below example, the `Tag` is used to specify that
     if `get_discriminator_value` returns `'apple'`, the input should be validated as an `ApplePie`, and if it
     returns `'pumpkin'`, the input should be validated as a `PumpkinPie`.
 
-    The primary role of the `Tag` here is to map the return value from the `CallableDiscriminator` function to
+    The primary role of the `Tag` here is to map the return value from the callable `Discriminator` function to
     the appropriate member of the `Union` in question.
 
     ```py
@@ -2460,7 +2460,7 @@ class Tag:
 
     from typing_extensions import Annotated, Literal
 
-    from pydantic import BaseModel, CallableDiscriminator, Tag
+    from pydantic import BaseModel, Discriminator, Tag
 
     class Pie(BaseModel):
         time_to_cook: int
@@ -2483,7 +2483,7 @@ class Tag:
                 Annotated[ApplePie, Tag('apple')],
                 Annotated[PumpkinPie, Tag('pumpkin')],
             ],
-            CallableDiscriminator(get_discriminator_value),
+            Discriminator(get_discriminator_value),
         ]
 
     apple_variation = ThanksgivingDinner.model_validate(
@@ -2510,8 +2510,8 @@ class Tag:
     ```
 
     !!! note
-        You must specify a `Tag` for every case in a `Union` that is associated with a `CallableDiscriminator`.
-        Failing to do so will result in a `PydanticUserError` with code
+        You must specify a `Tag` for every case in a `Union` that is associated with a
+        callable `Discriminator`. Failing to do so will result in a `PydanticUserError` with code
         [`callable-discriminator-no-tag`](../errors/usage_errors.md#callable-discriminator-no-tag).
 
     See the [Discriminated Unions](../concepts/unions.md#discriminated-unions)
@@ -2529,7 +2529,7 @@ class Tag:
 
 
 @_dataclasses.dataclass(**_internal_dataclass.slots_true, frozen=True)
-class CallableDiscriminator:
+class Discriminator:
     """Provides a way to use a custom callable as the way to extract the value of a union discriminator.
 
     This allows you to get validation behavior like you'd get from `Field(discriminator=<field_name>)`,
@@ -2538,7 +2538,7 @@ class CallableDiscriminator:
     Finally, this allows you to use a custom callable as the way to identify which member of a union a value
     belongs to, while still seeing all the performance benefits of a discriminated union.
 
-    Consider this example, which is much more performant with the use of `CallableDiscriminator` and thus a `TaggedUnion`
+    Consider this example, which is much more performant with the use of `Discriminator` and thus a `TaggedUnion`
     than it would be as a normal `Union`.
 
     ```py
@@ -2546,7 +2546,7 @@ class CallableDiscriminator:
 
     from typing_extensions import Annotated, Literal
 
-    from pydantic import BaseModel, CallableDiscriminator, Tag
+    from pydantic import BaseModel, Discriminator, Tag
 
     class Pie(BaseModel):
         time_to_cook: int
@@ -2569,7 +2569,7 @@ class Callab
```

</details>

---

## Case 3 — `309270da8d8b5032`

- **repo** `fastapi/fastapi` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** ➖ Drop support for Python 3.9 (#14897)
- **commit** https://github.com/fastapi/fastapi/commit/ad4e8e006016e088dbccdb73305a58a1338b1ad9
- **doc** `docs/en/docs/tutorial/body-multiple-params.md`
- **code** `fastapi/_compat/shared.py`
- **shared identifiers** `union`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/tutorial/body-multiple-params.md b/docs/en/docs/tutorial/body-multiple-params.md
index bb0c58368..d904fb839 100644
--- a/docs/en/docs/tutorial/body-multiple-params.md
+++ b/docs/en/docs/tutorial/body-multiple-params.md
@@ -106,13 +106,6 @@ As, by default, singular values are interpreted as query parameters, you don't h
 q: str | None = None
 ```
 
-Or in Python 3.9:
-
-```Python
-q: Union[str, None] = None
-```
-
-
 For example:
 
 {* ../../docs_src/body_multiple_params/tutorial004_an_py310.py hl[28] *}

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/fastapi/_compat/shared.py b/fastapi/_compat/shared.py
index c009da8fd..9d76dabe6 100644
--- a/fastapi/_compat/shared.py
+++ b/fastapi/_compat/shared.py
@@ -1,4 +1,3 @@
-import sys
 import types
 import typing
 import warnings
@@ -8,27 +7,26 @@ from dataclasses import is_dataclass
 from typing import (
     Annotated,
     Any,
+    TypeGuard,
     TypeVar,
     Union,
+    get_args,
+    get_origin,
 )
 
 from fastapi.types import UnionType
 from pydantic import BaseModel
 from pydantic.version import VERSION as PYDANTIC_VERSION
 from starlette.datastructures import UploadFile
-from typing_extensions import TypeGuard, get_args, get_origin
 
 _T = TypeVar("_T")
 
 # Copy from Pydantic: pydantic/_internal/_typing_extra.py
-if sys.version_info < (3, 10):
-    WithArgsTypes: tuple[Any, ...] = (typing._GenericAlias, types.GenericAlias)  # type: ignore[attr-defined]
-else:
-    WithArgsTypes: tuple[Any, ...] = (
-        typing._GenericAlias,  # type: ignore[attr-defined]
-        types.GenericAlias,
-        types.UnionType,
-    )  # pyright: ignore[reportAttributeAccessIssue]
+WithArgsTypes: tuple[Any, ...] = (
+    typing._GenericAlias,  # type: ignore[attr-defined]
+    types.GenericAlias,
+    types.UnionType,
+)  # pyright: ignore[reportAttributeAccessIssue]
 
 PYDANTIC_VERSION_MINOR_TUPLE = tuple(int(x) for x in PYDANTIC_VERSION.split(".")[:2])
 
@@ -47,7 +45,7 @@ sequence_types: tuple[type[Any], ...] = tuple(sequence_annotation_to_type.keys()
 
 # Copy of Pydantic: pydantic/_internal/_utils.py with added TypeGuard
 def lenient_issubclass(
-    cls: Any, class_or_tuple: Union[type[_T], tuple[type[_T], ...], None]
+    cls: Any, class_or_tuple: type[_T] | tuple[type[_T], ...] | None
 ) -> TypeGuard[type[_T]]:
     try:
         return isinstance(cls, type) and issubclass(cls, class_or_tuple)  # type: ignore[arg-type]
@@ -57,13 +55,13 @@ def lenient_issubclass(
         raise  # pragma: no cover
 
 
-def _annotation_is_sequence(annotation: Union[type[Any], None]) -> bool:
+def _annotation_is_sequence(annotation: type[Any] | None) -> bool:
     if lenient_issubclass(annotation, (str, bytes)):
         return False
     return lenient_issubclass(annotation, sequence_types)
 
 
-def field_annotation_is_sequence(annotation: Union[type[Any], None]) -> bool:
+def field_annotation_is_sequence(annotation: type[Any] | None) -> bool:
     origin = get_origin(annotation)
     if origin is Union or origin is UnionType:
         for arg in get_args(annotation):
@@ -79,7 +77,7 @@ def value_is_sequence(value: Any) -> bool:
     return isinstance(value, sequence_types) and not isinstance(value, (str, bytes))
 
 
-def _annotation_is_complex(annotation: Union[type[Any], None]) -> bool:
+def _annotation_is_complex(annotation: type[Any] | None) -> bool:
     return (
         lenient_issubclass(annotation, (BaseModel, Mapping, UploadFile))
         or _annotation_is_sequence(annotation)
@@ -87,7 +85,7 @@ def _annotation_is_complex(annotation: Union[type[Any], None]) -> bool:
     )
 
 
-def field_annotation_is_complex(annotation: Union[type[Any], None]) -> bool:
+def field_annotation_is_complex(annotation: type[Any] | None) -> bool:
     origin = get_origin(annotation)
     if origin is Union or origin is UnionType:
         return any(field_annotation_is_complex(arg) for arg in get_args(annotation))
@@ -108,7 +106,7 @@ def field_annotation_is_scalar(annotation: Any) -> bool:
     return annotation is Ellipsis or not field_annotation_is_complex(annotation)
 
 
-def field_annotation_is_scalar_sequence(annotation: Union[type[Any], None]) -> bool:
+def field_annotation_is_scalar_sequence(annotation: type[Any] | None) -> bool:
     origin = get_origin(annotation)
     if origin is Union or origin is UnionType:
         at_least_one_scalar_sequence = False

```

</details>

---

## Case 4 — `13ea17e67d714605`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** update pydantic-core to 2.4.0 (#6831)
- **commit** https://github.com/pydantic/pydantic/commit/55e09859fd02477d4c45adee09c0aeb3cf134ecb
- **doc** `docs/errors/validation_errors.md`
- **code** `pydantic/types.py`
- **shared identifiers** `uuid_version`, `validation`, `pydantic`, `uuid`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/errors/validation_errors.md b/docs/errors/validation_errors.md
index fd419ced6..bcc9dd6e8 100644
--- a/docs/errors/validation_errors.md
+++ b/docs/errors/validation_errors.md
@@ -1892,6 +1892,67 @@ except ValidationError as exc:
     #> 'url_type'
 ```
 
+## `uuid_parsing`
+
+This error is raised when the input value's type is not valid for a UUID field:
+
+```py
+from uuid import UUID
+
+from pydantic import BaseModel, ValidationError
+
+
+class Model(BaseModel):
+    u: UUID
+
+
+try:
+    Model(u='12345678-124-1234-1234-567812345678')
+except ValidationError as exc:
+    print(repr(exc.errors()[0]['type']))
+    #> 'uuid_parsing'
+```
+
+## `uuid_type`
+
+This error is raised when the input value's type is not valid instance for a UUID field (str, bytes or UUID):
+
+```py
+from uuid import UUID
+
+from pydantic import BaseModel, ValidationError
+
+
+class Model(BaseModel):
+    u: UUID
+
+
+try:
+    Model(u=1234567812412341234567812345678)
+except ValidationError as exc:
+    print(repr(exc.errors()[0]['type']))
+    #> 'uuid_type'
+```
+
+## `uuid_version`
+
+This error is raised when the input value's type is not match UUID version:
+
+```py
+from pydantic import UUID5, BaseModel, ValidationError
+
+
+class Model(BaseModel):
+    u: UUID5
+
+
+try:
+    Model(u='a6cc5730-2261-11ee-9c43-2eb5a363657c')
+except ValidationError as exc:
+    print(repr(exc.errors()[0]['type']))
+    #> 'uuid_version'
+```
+
 ## `value_error`
 
 This error is raised when a `ValueError` is raised during validation:

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/types.py b/pydantic/types.py
index 18803c491..9723e54df 100644
--- a/pydantic/types.py
+++ b/pydantic/types.py
@@ -542,16 +542,7 @@ class UuidVersion:
     def __get_pydantic_core_schema__(
         self, source: Any, handler: _annotated_handlers.GetCoreSchemaHandler
     ) -> core_schema.CoreSchema:
-        return core_schema.general_after_validator_function(
-            cast(core_schema.GeneralValidatorFunction, self.validate), handler(source)
-        )
-
-    def validate(self, value: UUID, _: core_schema.ValidationInfo) -> UUID:
-        if value.version != self.uuid_version:
-            raise PydanticCustomError(
-                'uuid_version', 'uuid version {required_version} expected', {'required_version': self.uuid_version}
-            )
-        return value
+        return core_schema.uuid_schema(version=self.uuid_version)
 
     def __hash__(self) -> int:
         return hash(type(self.uuid_version))

```

</details>

---

## Case 5 — `5a1c49e60bfd4f1f`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** s/1.0/0.11/ in versionadded/versionchanged markers
- **commit** https://github.com/pallets/flask/commit/c5900a1adf8e868eca745225f3cf32218cdbbb23
- **doc** `docs/config.rst`
- **code** `flask/json.py`
- **shared identifiers** `ver:0.11`, `ver:1.0`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/config.rst b/docs/config.rst
index 1d9445d3..3039b3ea 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -241,7 +241,7 @@ The following configuration values are used internally by Flask:
 .. versionadded:: 0.10
    ``JSON_AS_ASCII``, ``JSON_SORT_KEYS``, ``JSONIFY_PRETTYPRINT_REGULAR``
 
-.. versionadded:: 1.0
+.. versionadded:: 0.11
    ``SESSION_REFRESH_EACH_REQUEST``, ``TEMPLATES_AUTO_RELOAD``,
    ``LOGGER_HANDLER_POLICY``, ``EXPLAIN_TEMPLATE_LOADING``
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/json.py b/flask/json.py
index 2bd47902..b9ce4a08 100644
--- a/flask/json.py
+++ b/flask/json.py
@@ -235,7 +235,7 @@ def jsonify(*args, **kwargs):
         }
 
 
-    .. versionchanged:: 1.0
+    .. versionchanged:: 0.11
        Added support for serializing top-level arrays. This introduces a
        security risk in ancient browsers. See :ref:`json-security` for details.
 

```

</details>

---

## Case 6 — `9e961b90308e38c5`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Json schema modify function as middleware (#5570)
- **commit** https://github.com/pydantic/pydantic/commit/c8b978ecd4136fa41baed58dee7d50cf6280cee5
- **doc** `docs/usage/schema.md`
- **code** `pydantic/_internal/_dataclasses.py`
- **shared identifiers** `pydantic`, `schema`, `core`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/schema.md b/docs/usage/schema.md
index 294757452..bfddb48bc 100644
--- a/docs/usage/schema.md
+++ b/docs/usage/schema.md
@@ -3,13 +3,17 @@
 ```py output="json"
 import json
 from enum import Enum
+from typing import Union
+
+from typing_extensions import Annotated
 
 from pydantic import BaseModel, Field
+from pydantic.config import ConfigDict
 
 
 class FooBar(BaseModel):
     count: int
-    size: float = None
+    size: Union[float, None] = None
 
 
 class Gender(str, Enum):
@@ -24,10 +28,10 @@ class MainModel(BaseModel):
     This is the description of the main model
     """
 
-    model_config = dict(title='Main')
+    model_config = ConfigDict(title='Main')
 
-    foo_bar: FooBar = Field(...)
-    gender: Gender = Field(None, alias='Gender')
+    foo_bar: FooBar
+    gender: Annotated[Union[Gender, None], Field(alias='Gender')] = None
     snap: int = Field(
         42,
         title='The Snap',
@@ -40,17 +44,18 @@ class MainModel(BaseModel):
 print(json.dumps(MainModel.model_json_schema(), indent=2))
 """
 {
-  "title": "Main",
-  "description": "This is the description of the main model",
   "type": "object",
   "properties": {
     "foo_bar": {
       "$ref": "#/$defs/FooBar"
     },
     "Gender": {
-      "allOf": [
+      "anyOf": [
         {
           "$ref": "#/$defs/Gender"
+        },
+        {
+          "type": "null"
         }
       ],
       "default": null
@@ -67,9 +72,10 @@ print(json.dumps(MainModel.model_json_schema(), indent=2))
   "required": [
     "foo_bar"
   ],
+  "title": "Main",
+  "description": "\n    This is the description of the main model\n    ",
   "$defs": {
     "FooBar": {
-      "title": "FooBar",
       "type": "object",
       "properties": {
         "count": {
@@ -77,14 +83,22 @@ print(json.dumps(MainModel.model_json_schema(), indent=2))
           "title": "Count"
         },
         "size": {
-          "type": "number",
+          "anyOf": [
+            {
+              "type": "number"
+            },
+            {
+              "type": "null"
+            }
+          ],
           "default": null,
           "title": "Size"
         }
       },
       "required": [
         "count"
-      ]
+      ],
+      "title": "FooBar"
     },
     "Gender": {
       "enum": [
@@ -175,7 +189,6 @@ print(schema_json_of(Pet, title='The Pet Schema', indent=2))
   },
   "$defs": {
     "Cat": {
-      "title": "Cat",
       "type": "object",
       "properties": {
         "pet_type": {
@@ -190,10 +203,10 @@ print(schema_json_of(Pet, title='The Pet Schema', indent=2))
       "required": [
         "pet_type",
         "cat_name"
-      ]
+      ],
+      "title": "Cat"
     },
     "Dog": {
-      "title": "Dog",
       "type": "object",
       "properties": {
         "pet_type": {
@@ -208,7 +221,8 @@ print(schema_json_of(Pet, title='The Pet Schema', indent=2))
       "required": [
         "pet_type",
         "dog_name"
-      ]
+      ],
+      "title": "Dog"
     }
   },
   "title": "The Pet Schema"
@@ -317,7 +331,6 @@ class ModelB(BaseModel):
 print(ModelB.model_json_schema())
 """
 {
-    'title': 'ModelB',
     'type': 'object',
     'properties': {
         'foo': {
@@ -328,6 +341,7 @@ print(ModelB.model_json_schema())
         }
     },
     'required': ['foo'],
+    'title': 'ModelB',
 }
 """
 ```
@@ -370,11 +384,12 @@ Here is an example of a custom type that *overrides* the generated core schema:
 
 ```py
 from dataclasses import dataclass
-from typing import Any, Callable, Dict, List, Type
+from typing import Any, Dict, List, Type
 
 from pydantic_core import core_schema
 
 from pydantic import BaseModel
+from pydantic.json_schema import GetJsonSchemaHandler
 
 
 @dataclass
@@ -387,7 +402,7 @@ class CompressedString:
 
     @classmethod
     def __get_pydantic_core_schema__(
-        cls, source: Type[Any], handler: Callable[[Type[Any]], core_schema.CoreSchema]
+        cls, source: Type[Any], handler: GetJsonSchemaHandler
     ) -> core_sche
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/_internal/_dataclasses.py b/pydantic/_internal/_dataclasses.py
index 11380861e..9747d7fb0 100644
--- a/pydantic/_internal/_dataclasses.py
+++ b/pydantic/_internal/_dataclasses.py
@@ -6,7 +6,7 @@ from __future__ import annotations as _annotations
 import dataclasses
 import typing
 import warnings
-from functools import wraps
+from functools import partial, wraps
 from typing import Any, Callable, ClassVar
 
 from pydantic_core import ArgsKwargs, SchemaSerializer, SchemaValidator, core_schema
@@ -82,7 +82,11 @@ def complete_dataclass(
     )
 
     try:
-        schema = gen_schema.generate_schema(cls)
+        get_core_schema = getattr(cls, '__get_pydantic_core_schema__', None)
+        if get_core_schema:
+            schema = get_core_schema(cls, partial(gen_schema.generate_schema, from_dunder_get_core_schema=False))
+        else:
+            schema = gen_schema.generate_schema(cls, False)
     except PydanticUndefinedAnnotation as e:
         if raise_errors:
             raise

```

</details>

---

## Case 7 — `da90a6706ce1be6e`

- **repo** `encode/httpx` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Switch follow redirects default (#1808)
- **commit** https://github.com/encode/httpx/commit/47266d763bdef9dc99f9c9d09d49d441b87802e6
- **doc** `docs/quickstart.md`
- **code** `httpx/_api.py`
- **shared identifiers** `follow_redirects`, `allow_redirects`, `redirects`, `follow`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/quickstart.md b/docs/quickstart.md
index 4afaff2..23e1765 100644
--- a/docs/quickstart.md
+++ b/docs/quickstart.md
@@ -128,7 +128,7 @@ Often Web API responses will be encoded as JSON.
 To include additional headers in the outgoing request, use the `headers` keyword argument:
 
 ```pycon
->>> url = 'http://httpbin.org/headers'
+>>> url = 'https://httpbin.org/headers'
 >>> headers = {'user-agent': 'my-app/0.0.1'}
 >>> r = httpx.get(url, headers=headers)
 ```
@@ -380,7 +380,7 @@ If you're using streaming responses in any of these ways then the `response.cont
 Any cookies that are set on the response can be easily accessed:
 
 ```pycon
->>> r = httpx.get('http://httpbin.org/cookies/set?chocolate=chip', allow_redirects=False)
+>>> r = httpx.get('https://httpbin.org/cookies/set?chocolate=chip')
 >>> r.cookies['chocolate']
 'chip'
 ```
@@ -389,7 +389,7 @@ To include cookies in an outgoing request, use the `cookies` parameter:
 
 ```pycon
 >>> cookies = {"peanut": "butter"}
->>> r = httpx.get('http://httpbin.org/cookies', cookies=cookies)
+>>> r = httpx.get('https://httpbin.org/cookies', cookies=cookies)
 >>> r.json()
 {'cookies': {'peanut': 'butter'}}
 ```
@@ -408,35 +408,37 @@ with additional API for accessing cookies by their domain or path.
 
 ## Redirection and History
 
-By default, HTTPX will follow redirects for all HTTP methods.
-
-
-The `history` property of the response can be used to inspect any followed redirects.
-It contains a list of any redirect responses that were followed, in the order
-in which they were made.
+By default, HTTPX will **not** follow redirects for all HTTP methods, although
+this can be explicitly enabled.
 
 For example, GitHub redirects all HTTP requests to HTTPS.
 
 ```pycon
 >>> r = httpx.get('http://github.com/')
->>> r.url
-URL('https://github.com/')
 >>> r.status_code
-200
+301
 >>> r.history
-[<Response [301 Moved Permanently]>]
+[]
+>>> r.next_request
+<Request('GET', 'https://github.com/')>
 ```
 
-You can modify the default redirection handling with the allow_redirects parameter:
+You can modify the default redirection handling with the `follow_redirects` parameter:
 
 ```pycon
->>> r = httpx.get('http://github.com/', allow_redirects=False)
+>>> r = httpx.get('http://github.com/', follow_redirects=True)
+>>> r.url
+URL('https://github.com/')
 >>> r.status_code
-301
+200
 >>> r.history
-[]
+[<Response [301 Moved Permanently]>]
 ```
 
+The `history` property of the response can be used to inspect any followed redirects.
+It contains a list of any redirect responses that were followed, in the order
+in which they were made.
+
 ## Timeouts
 
 HTTPX defaults to including reasonable timeouts for all network operations,

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/httpx/_api.py b/httpx/_api.py
index da81853..eb81d46 100644
--- a/httpx/_api.py
+++ b/httpx/_api.py
@@ -34,7 +34,7 @@ def request(
     auth: AuthTypes = None,
     proxies: ProxiesTypes = None,
     timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
-    allow_redirects: bool = True,
+    follow_redirects: bool = False,
     verify: VerifyTypes = True,
     cert: CertTypes = None,
     trust_env: bool = True,
@@ -66,7 +66,7 @@ def request(
     * **proxies** - *(optional)* A dictionary mapping proxy keys to proxy URLs.
     * **timeout** - *(optional)* The timeout configuration to use when sending
     the request.
-    * **allow_redirects** - *(optional)* Enables or disables HTTP redirects.
+    * **follow_redirects** - *(optional)* Enables or disables HTTP redirects.
     * **verify** - *(optional)* SSL certificates (a.k.a CA bundle) used to
     verify the identity of requested hosts. Either `True` (default CA bundle),
     a path to an SSL certificate file, an `ssl.SSLContext`, or `False`
@@ -107,7 +107,7 @@ def request(
             params=params,
             headers=headers,
             auth=auth,
-            allow_redirects=allow_redirects,
+            follow_redirects=follow_redirects,
         )
 
 
@@ -126,7 +126,7 @@ def stream(
     auth: AuthTypes = None,
     proxies: ProxiesTypes = None,
     timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
-    allow_redirects: bool = True,
+    follow_redirects: bool = False,
     verify: VerifyTypes = True,
     cert: CertTypes = None,
     trust_env: bool = True,
@@ -159,7 +159,7 @@ def stream(
             params=params,
             headers=headers,
             auth=auth,
-            allow_redirects=allow_redirects,
+            follow_redirects=follow_redirects,
         ) as response:
             yield response
 
@@ -172,7 +172,7 @@ def get(
     cookies: CookieTypes = None,
     auth: AuthTypes = None,
     proxies: ProxiesTypes = None,
-    allow_redirects: bool = True,
+    follow_redirects: bool = False,
     cert: CertTypes = None,
     verify: VerifyTypes = True,
     timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
@@ -194,7 +194,7 @@ def get(
         cookies=cookies,
         auth=auth,
         proxies=proxies,
-        allow_redirects=allow_redirects,
+        follow_redirects=follow_redirects,
         cert=cert,
         verify=verify,
         timeout=timeout,
@@ -210,7 +210,7 @@ def options(
     cookies: CookieTypes = None,
     auth: AuthTypes = None,
     proxies: ProxiesTypes = None,
-    allow_redirects: bool = True,
+    follow_redirects: bool = False,
     cert: CertTypes = None,
     verify: VerifyTypes = True,
     timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
@@ -232,7 +232,7 @@ def options(
         cookies=cookies,
         auth=auth,
         proxies=proxies,
-        allow_redirects=allow_redirects,
+        follow_redirects=follow_redirects,
         cert=cert,
         verify=verify,
         timeout=timeout,
@@ -248,7 +248,7 @@ def head(
     cookies: CookieTypes = None,
     auth: AuthTypes = None,
     proxies: ProxiesTypes = None,
-    allow_redirects: bool = True,
+    follow_redirects: bool = False,
     cert: CertTypes = None,
     verify: VerifyTypes = True,
     timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
@@ -270,7 +270,7 @@ def head(
         cookies=cookies,
         auth=auth,
         proxies=proxies,
-        allow_redirects=allow_redirects,
+        follow_redirects=follow_redirects,
         cert=cert,
         verify=verify,
         timeout=timeout,
@@ -290,7 +290,7 @@ def post(
     cookies: CookieTypes = None,
     auth: AuthTypes = None,
     proxies: ProxiesTypes = None,
-    allow_redirects: bool = True,
+    follow_redirects: bool = False,
     cert: CertTypes = None,
     verify: VerifyTypes = True,
     timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
@@ -313,7 +313,7 @@ def post(
         cookies=cookies,
         auth=auth,
         proxies=proxies,
-        allow_redirects=allow_redirects,
+
```

</details>

---

## Case 8 — `ccfbf57763ca6ea2`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add CallableDiscriminator and Tag (#7983)
- **commit** https://github.com/pydantic/pydantic/commit/9868b456e4352558aa01217a6688b30554c6f290
- **doc** `docs/errors/usage_errors.md`
- **code** `pydantic/fields.py`
- **shared identifiers** `callablediscriminator`, `discriminator`, `callable`, `union`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/errors/usage_errors.md b/docs/errors/usage_errors.md
index 630a8690f..fbef1aae3 100644
--- a/docs/errors/usage_errors.md
+++ b/docs/errors/usage_errors.md
@@ -365,6 +365,62 @@ class Model(BaseModel):
 assert Model(pet={'pet_type': 'kitten'}).pet.pet_type == 'cat'
 ```
 
+## Callable discriminator case with no tag {#callable-discriminator-no-tag}
+
+This error is raised when a `Union` that uses a `CallableDiscriminator` doesn't have `Tag` annotations for all cases.
+
+```py
+from typing import Union
+
+from typing_extensions import Annotated
+
+from pydantic import BaseModel, CallableDiscriminator, PydanticUserError, Tag
+
+
+def model_x_discriminator(v):
+    if isinstance(v, str):
+        return 'str'
+    if isinstance(v, (dict, BaseModel)):
+        return 'model'
+
+
+# tag missing for both union choices
+try:
+
+    class DiscriminatedModel(BaseModel):
+        x: Annotated[
+            Union[str, 'DiscriminatedModel'],
+            CallableDiscriminator(model_x_discriminator),
+        ]
+
+except PydanticUserError as exc_info:
+    assert exc_info.code == 'callable-discriminator-no-tag'
+
+# tag missing for `'DiscriminatedModel'` union choice
+try:
+
+    class DiscriminatedModel(BaseModel):
+        x: Annotated[
+            Union[Annotated[str, Tag('str')], 'DiscriminatedModel'],
+            CallableDiscriminator(model_x_discriminator),
+        ]
+
+except PydanticUserError as exc_info:
+    assert exc_info.code == 'callable-discriminator-no-tag'
+
+# tag missing for `str` union choice
+try:
+
+    class DiscriminatedModel(BaseModel):
+        x: Annotated[
+            Union[str, Annotated['DiscriminatedModel', Tag('model')]],
+            CallableDiscriminator(model_x_discriminator),
+        ]
+
+except PydanticUserError as exc_info:
+    assert exc_info.code == 'callable-discriminator-no-tag'
+```
+
 
 ## `TypedDict` version {#typed-dict-version}
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/fields.py b/pydantic/fields.py
index c54ae72b2..c2d91a302 100644
--- a/pydantic/fields.py
+++ b/pydantic/fields.py
@@ -64,7 +64,7 @@ class _FromFieldInfoInputs(typing_extensions.TypedDict, total=False):
     max_digits: int | None
     decimal_places: int | None
     union_mode: Literal['smart', 'left_to_right'] | None
-    discriminator: str | None
+    discriminator: str | types.CallableDiscriminator | None
     json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None
     frozen: bool | None
     validate_default: bool | None
@@ -101,7 +101,7 @@ class FieldInfo(_repr.Representation):
         description: The description of the field.
         examples: List of examples of the field.
         exclude: Whether to exclude the field from the model serialization.
-        discriminator: Field name for discriminating the type in a tagged union.
+        discriminator: Field name or CallableDiscriminator for discriminating the type in a tagged union.
         json_schema_extra: Dictionary of extra JSON schema properties.
         frozen: Whether the field is frozen.
         validate_default: Whether to validate the default value of the field.
@@ -122,7 +122,7 @@ class FieldInfo(_repr.Representation):
     description: str | None
     examples: list[Any] | None
     exclude: bool | None
-    discriminator: str | None
+    discriminator: str | types.CallableDiscriminator | None
     json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None
     frozen: bool | None
     validate_default: bool | None
@@ -682,7 +682,7 @@ def Field(  # noqa: C901
     description: str | None = _Unset,
     examples: list[Any] | None = _Unset,
     exclude: bool | None = _Unset,
-    discriminator: str | None = _Unset,
+    discriminator: str | types.CallableDiscriminator | None = _Unset,
     json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
     frozen: bool | None = _Unset,
     validate_default: bool | None = _Unset,
@@ -727,7 +727,7 @@ def Field(  # noqa: C901
         description: Human-readable description.
         examples: Example values for this field.
         exclude: Whether to exclude the field from the model serialization.
-        discriminator: Field name for discriminating the type in a tagged union.
+        discriminator: Field name or CallableDiscriminator for discriminating the type in a tagged union.
         json_schema_extra: Any additional JSON schema data for the schema property.
         frozen: Whether the field is frozen.
         validate_default: Run validation that isn't only checking existence of defaults. This can be set to `True` or `False`. If not set, it defaults to `None`.

```

</details>

---

## Case 9 — `f3e38d8198dff968`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Rewrite serialization documentation (#12018)
- **commit** https://github.com/pydantic/pydantic/commit/ffc084053b1ed87927c4c10e6dc2d17f6a4f2cac
- **doc** `docs/concepts/models.md`
- **code** `pydantic/main.py`
- **shared identifiers** `model_dump_json`, `serialization`, `model_copy`, `model_dump`, `models`, `model`, `copy`, `dump`, `json`, `mode`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/concepts/models.md b/docs/concepts/models.md
index 7de694afe..39ad9630f 100644
--- a/docs/concepts/models.md
+++ b/docs/concepts/models.md
@@ -155,10 +155,10 @@ Models possess the following methods and attributes:
 * [`model_construct()`][pydantic.main.BaseModel.model_construct]: Creates models without running validation. See
     [Creating models without validation](#creating-models-without-validation).
 * [`model_dump()`][pydantic.main.BaseModel.model_dump]: Returns a dictionary of the model's fields and values. See
-    [Serialization](serialization.md#model_dump).
-* [`model_dump_json()`][pydantic.main.BaseModel.model_dump_json]: Returns a JSON string representation of [`model_dump()`][pydantic.main.BaseModel.model_dump]. See [Serialization](serialization.md#model_dump_json).
+    [Serialization](serialization.md#python-mode).
+* [`model_dump_json()`][pydantic.main.BaseModel.model_dump_json]: Returns a JSON string representation of [`model_dump()`][pydantic.main.BaseModel.model_dump]. See [Serialization](serialization.md#json-mode).
 * [`model_copy()`][pydantic.main.BaseModel.model_copy]: Returns a copy (by default, shallow copy) of the model. See
-    [Serialization](serialization.md#model_copy).
+    [Model copy](#model-copy).
 * [`model_json_schema()`][pydantic.main.BaseModel.model_json_schema]: Returns a jsonable dictionary representing the model's JSON Schema. See [JSON Schema](json_schema.md).
 * [`model_fields`][pydantic.main.BaseModel.model_fields]: A mapping between field names and their definitions ([`FieldInfo`][pydantic.fields.FieldInfo] instances).
 * [`model_computed_fields`][pydantic.main.BaseModel.model_computed_fields]: A mapping between computed field names and their definitions ([`ComputedFieldInfo`][pydantic.fields.ComputedFieldInfo] instances).
@@ -695,6 +695,41 @@ Here are some additional notes on the behavior of [`model_construct()`][pydantic
     not stored in `__pydantic_extra__` or `__dict__` on the instance.
     * Unlike when instantiating the model with validation, a call to [`model_construct()`][pydantic.main.BaseModel.model_construct] with [`extra`][pydantic.ConfigDict.extra] set to `'forbid'` doesn't raise an error in the presence of data not corresponding to fields. Rather, said input data is simply ignored.
 
+## Model copy
+
+??? api "API Documentation"
+    [`pydantic.main.BaseModel.model_copy`][pydantic.main.BaseModel.model_copy]<br>
+
+The [`model_copy()`][pydantic.BaseModel.model_copy] method allows models to be duplicated (with optional updates),
+which is particularly useful when working with frozen models.
+
+```python
+from pydantic import BaseModel
+
+
+class BarModel(BaseModel):
+    whatever: int
+
+
+class FooBarModel(BaseModel):
+    banana: float
+    foo: str
+    bar: BarModel
+
+
+m = FooBarModel(banana=3.14, foo='hello', bar={'whatever': 123})
+
+print(m.model_copy(update={'banana': 0}))
+#> banana=0 foo='hello' bar=BarModel(whatever=123)
+
+# normal copy gives the same object reference for bar:
+print(id(m.bar) == id(m.model_copy().bar))
+#> True
+# deep copy gives a new object reference for `bar`:
+print(id(m.bar) == id(m.model_copy(deep=True).bar))
+#> False
+```
+
 ## Generic models
 
 Pydantic supports the creation of generic models to make it easier to reuse a common model structure. Both the new
@@ -1529,7 +1564,7 @@ Field order affects models in the following ways:
 
 * field order is preserved in the model [JSON Schema](json_schema.md)
 * field order is preserved in [validation errors](#error-handling)
-* field order is preserved by [`.model_dump()` and `.model_dump_json()` etc.](serialization.md#model_dump)
+* field order is preserved when [serializing data](serialization.md#serializing-data)
 
 ```python
 from pydantic import BaseModel, ValidationError

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/main.py b/pydantic/main.py
index fde9d26ba..0c5108966 100644
--- a/pydantic/main.py
+++ b/pydantic/main.py
@@ -386,7 +386,7 @@ class BaseModel(metaclass=_model_construction.ModelMetaclass):
 
     def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
         """!!! abstract "Usage Documentation"
-            [`model_copy`](../concepts/serialization.md#model_copy)
+            [`model_copy`](../concepts/models.md#model-copy)
 
         Returns a copy of the model.
 
@@ -435,7 +435,7 @@ class BaseModel(metaclass=_model_construction.ModelMetaclass):
         serialize_as_any: bool = False,
     ) -> dict[str, Any]:
         """!!! abstract "Usage Documentation"
-            [`model_dump`](../concepts/serialization.md#modelmodel_dump)
+            [`model_dump`](../concepts/serialization.md#python-mode)
 
         Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.
 
@@ -494,7 +494,7 @@ class BaseModel(metaclass=_model_construction.ModelMetaclass):
         serialize_as_any: bool = False,
     ) -> str:
         """!!! abstract "Usage Documentation"
-            [`model_dump_json`](../concepts/serialization.md#modelmodel_dump_json)
+            [`model_dump_json`](../concepts/serialization.md#json-mode)
 
         Generates a JSON representation of the model using Pydantic's `to_json` method.
 

```

</details>

---

## Case 10 — `e67425787b988743`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add support for `EllipsisType` (#13484)
- **commit** https://github.com/pydantic/pydantic/commit/c4eac98eba19e48fc4414a33f973299b08f3ac55
- **doc** `docs/errors/validation_errors.md`
- **code** `pydantic-core/src/serializers/type_serializers/mod.rs`
- **shared identifiers** `ellipsis`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/errors/validation_errors.md b/docs/errors/validation_errors.md
index b0d509b97..fc0539fef 100644
--- a/docs/errors/validation_errors.md
+++ b/docs/errors/validation_errors.md
@@ -724,6 +724,27 @@ except ValidationError as exc:
     #> 'dict_type'
 ```
 
+## `ellipsis_error`
+
+This error is raised when the input isn't the [`Ellipsis`][] literal:
+
+```python
+from types import EllipsisType
+
+from pydantic import BaseModel, ValidationError
+
+
+class Model(BaseModel):
+    e: EllipsisType
+
+
+try:
+    Model(e=1)
+except ValidationError as exc:
+    print(repr(exc.errors()[0]['type']))
+    #> 'ellipsis_error'
+```
+
 ## `enum`
 
 This error is raised when the input value does not exist in an `enum` field members:

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic-core/src/serializers/type_serializers/mod.rs b/pydantic-core/src/serializers/type_serializers/mod.rs
index da95113ea..ad664e8f8 100644
--- a/pydantic-core/src/serializers/type_serializers/mod.rs
+++ b/pydantic-core/src/serializers/type_serializers/mod.rs
@@ -6,6 +6,7 @@ pub mod datetime_etc;
 pub mod decimal;
 pub mod definitions;
 pub mod dict;
+pub mod ellipsis;
 pub mod enum_;
 pub mod float;
 pub mod format;

```

</details>

---

## Case 11 — `006e62048527c895`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Improve the rendering of the conversion table (#6275)
- **commit** https://github.com/pydantic/pydantic/commit/0bde99751e23239ab7ccd9159d26be87c2b341e1
- **doc** `docs/usage/conversion_table.md`
- **code** `docs/plugins/conversion_table.py`
- **shared identifiers** `conversion_table`, `conversion`, `strict`, `table`, `json`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/conversion_table.md b/docs/usage/conversion_table.md
index fed7ed035..3f941500d 100644
--- a/docs/usage/conversion_table.md
+++ b/docs/usage/conversion_table.md
@@ -4,4 +4,17 @@ The following table provides details on how Pydantic converts data during valida
 
 See [Strict Mode](models.md#strict-mode) for more details.
 
-{{ conversion_table }}
+=== "All"
+{{ conversion_table_all }}
+
+=== "JSON"
+{{ conversion_table_json }}
+
+=== "JSON - Strict"
+{{ conversion_table_json_strict }}
+
+=== "Python"
+{{ conversion_table_python }}
+
+=== "Python - Strict"
+{{ conversion_table_python_strict }}

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/docs/plugins/conversion_table.py b/docs/plugins/conversion_table.py
index 1a0d49323..5093afc08 100644
--- a/docs/plugins/conversion_table.py
+++ b/docs/plugins/conversion_table.py
@@ -7,42 +7,115 @@ from dataclasses import dataclass
 from datetime import date, datetime, time, timedelta
 from decimal import Decimal
 from enum import Enum, IntEnum
+from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
 from pathlib import Path
-from typing import Any, Iterable, Literal, Mapping, Pattern, Sequence, Type
+from typing import Any, Iterable, Mapping, Pattern, Sequence, Type
 from uuid import UUID
 
 from pydantic_core import CoreSchema, core_schema
 from typing_extensions import TypedDict
 
-from pydantic import ByteSize
-from pydantic.networks import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
+from pydantic import ByteSize, InstanceOf
 
 
 @dataclass
 class Row:
-    field_type: type[Any]
-    input_type: type[Any]
-    mode: Literal['Lax', 'Strict']
-    input_format: Literal['Python', 'JSON', 'Python & JSON']
+    field_type: type[Any] | str
+    input_type: type[Any] | str
+    python_input: bool = False
+    json_input: bool = False
+    strict: bool = False
     condition: str | None = None
     valid_examples: list[Any] | None = None
     invalid_examples: list[Any] | None = None
     core_schemas: list[type[CoreSchema]] | None = None
 
+    @property
+    def field_type_str(self) -> str:
+        return f'{self.field_type.__name__}' if hasattr(self.field_type, '__name__') else f'{self.field_type}'
 
-table: list[Row] = [
+    @property
+    def input_type_str(self) -> str:
+        return f'{self.input_type.__name__}' if hasattr(self.input_type, '__name__') else f'{self.input_type}'
+
+    @property
+    def input_source_str(self) -> str:
+        if self.python_input:
+            if self.json_input:
+                return 'Python & JSON'
+            else:
+                return 'Python'
+        elif self.json_input:
+            return 'JSON'
+        else:
+            return ''
+
+
+@dataclass
+class ConversionTable:
+    rows: list[Row]
+
+    col_names = [
+        'Field Type',
+        'Input',
+        'Strict',
+        'Input Source',
+        'Conditions',
+    ]
+    open_nowrap_span = '<span style="white-space: nowrap;">'
+    close_nowrap_span = '</span>'
+
+    def col_values(self, row: Row) -> list[str]:
+        o = self.open_nowrap_span
+        c = self.close_nowrap_span
+
+        return [
+            f'{o}`{row.field_type_str}`{c}',
+            f'{o}`{row.input_type_str}`{c}',
+            '✓' if row.strict else '',
+            f'{o}{row.input_source_str}{c}',
+            row.condition if row.condition else '',
+        ]
+
+    @staticmethod
+    def row_as_markdown(cols: list[str]) -> str:
+        return f'| {" | ".join(cols)} |'
+
+    def as_markdown(self) -> str:
+        lines = [self.row_as_markdown(self.col_names), self.row_as_markdown(['-'] * len(self.col_names))]
+        for row in self.rows:
+            lines.append(self.row_as_markdown(self.col_values(row)))
+        return '\n'.join(lines)
+
+    @staticmethod
+    def row_sort_key(row: Row) -> Any:
+        field_type = row.field_type_str or ' '
+        input_type = row.input_type_str or ' '
+        input_source = row.input_source_str
+
+        # Include the .isupper() to make it so that leading-lowercase items come first
+        return field_type[0].isupper(), field_type, input_type[0].isupper(), input_type, input_source
+
+    def sorted(self) -> ConversionTable:
+        return ConversionTable(sorted(self.rows, key=self.row_sort_key))
+
+    def filtered(self, predicate: typing.Callable[[Row], bool]) -> ConversionTable:
+        return ConversionTable([row for row in self.rows if predicate(row)])
+
+
+table_rows: list[Row] = [
     Row(
         str,
         str,
-        'Strict',
-        'Python & JSON',
+        strict=
```

</details>

---

## Case 12 — `44f0e1686fd839d4`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Minor docs updates based on issues with docs flags (#7816)
- **commit** https://github.com/pydantic/pydantic/commit/3dac7435b6bb2bb3e74891d1b7311351dbcf92f8
- **doc** `docs/concepts/models.md`
- **code** `pydantic/config.py`
- **shared identifiers** `serialization`, `model_dump`, `validation`, `basemodel`, `pydantic`, `another`, `typing`, `field`, `model`, `base`, `dump`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/concepts/models.md b/docs/concepts/models.md
index ca5f6cc6a..852f06c7c 100644
--- a/docs/concepts/models.md
+++ b/docs/concepts/models.md
@@ -102,7 +102,7 @@ Models possess the following methods and attributes:
     [Serialization](serialization.md#modeldumpjson).
 * `model_extra`: get extra fields set during validation.
 * `model_fields_set`: set of fields which were set when the model instance was initialized.
-* `model_json_schema()`: returns a dictionary representing the model as JSON Schema. See [JSON Schema](json_schema.md).
+* `model_json_schema()`: returns a jsonable dictionary representing the model as JSON Schema. See [JSON Schema](json_schema.md).
 * `model_modify_json_schema()`: a method for how the "generic" properties of the JSON schema are populated.
     See [JSON Schema](json_schema.md).
 * `model_parametrized_name()`: compute the class name for parametrizations of generic classes.
@@ -777,16 +777,10 @@ except ValidationError as e:
 When using bound type parameters, and when leaving type parameters unspecified, Pydantic treats generic models
 similarly to how it treats built-in generic types like `List` and `Dict`:
 
-* If you don't specify parameters before instantiating the generic model, they are treated as the bound of the `TypeVar`.
+* If you don't specify parameters before instantiating the generic model, they are validated as the bound of the `TypeVar`.
 * If the `TypeVar`s involved have no bounds, they are treated as `Any`.
 
-Also, like `List` and `Dict`, any parameters specified using a `TypeVar` can later be substituted with concrete types.
-
-!!! note
-    For serialization this means: when a `TypeVar` is constrained or bound using a parent model `ParentModel`
-    and a child model `ChildModel` is used as a concrete value, Pydantic will serialize `ChildModel` as `ParentModel`.
-    `TypeVar` needs to be wrapped inside [`SerializeAsAny`](serialization.md#serializing-with-duck-typing)
-    for Pydantic to serialize `ChildModel` as `ChildModel`.
+Also, like `List` and `Dict`, any parameters specified using a `TypeVar` can later be substituted with concrete types:
 
 ```py requires="3.12"
 from typing import Generic, TypeVar
@@ -884,7 +878,43 @@ assert error.model_dump() == {
 }
 ```
 
-If you use a `default=...` (available in Python >= 3.13 or via `typing-extensions`) or constraints (`TypeVar('T', str, int)`; note that you rarely want to use this form of a `TypeVar`) then the default value or constraints will be used for both validation and serialization if the type variable is not parametrized. You can override this behavior using `pydantic.SerializeAsAny`:
+Here's another example of the above behavior, enumerating all permutations regarding bound specification and generic type parametrization:
+```py
+from typing import Generic
+
+from typing_extensions import TypeVar
+
+from pydantic import BaseModel
+
+TBound = TypeVar('TBound', bound=BaseModel)
+TNoBound = TypeVar('TNoBound')
+
+
+class IntValue(BaseModel):
+    value: int
+
+
+class ItemBound(BaseModel, Generic[TBound]):
+    item: TBound
+
+
+class ItemNoBound(BaseModel, Generic[TNoBound]):
+    item: TNoBound
+
+
+item_bound_inferred = ItemBound(item=IntValue(value=3))
+item_bound_explicit = ItemBound[IntValue](item=IntValue(value=3))
+item_no_bound_inferred = ItemNoBound(item=IntValue(value=3))
+item_no_bound_explicit = ItemNoBound[IntValue](item=IntValue(value=3))
+
+# calling `print(x.model_dump())` on any of the above instances results in the following:
+#> {'item': {'value': 3}}
+```
+
+If you use a `default=...` (available in Python >= 3.13 or via `typing-extensions`) or constraints (`TypeVar('T', str, int)`;
+note that you rarely want to use this form of a `TypeVar`) then the default value or constraints will be used for both
+validation and serialization if the type variable is not parametrized.
+You can override this behavior using `pydantic.SerializeAsAny`:
 
 ```py
 from typing import Generic, Optional
@@ -942,6 
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/config.py b/pydantic/config.py
index 89f5bd103..a88a8df4b 100644
--- a/pydantic/config.py
+++ b/pydantic/config.py
@@ -164,6 +164,40 @@ class ConfigDict(TypedDict, total=False):
     """
     Whether to populate models with the `value` property of enums, rather than the raw enum.
     This may be useful if you want to serialize `model.model_dump()` later. Defaults to `False`.
+
+    !!! note
+        If you have an `Optional[Enum]` value that you set a default for, you need to use `validate_default=True`
+        for said Field to ensure that the `use_enum_values` flag takes effect on the default, as extracting an
+        enum's value occurs during validation, not serialization.
+
+    ```py
+    from enum import Enum
+    from typing import Optional
+
+    from pydantic import BaseModel, ConfigDict, Field
+
+
+    class SomeEnum(Enum):
+        FOO = 'foo'
+        BAR = 'bar'
+        BAZ = 'baz'
+
+
+    class SomeModel(BaseModel):
+        model_config = ConfigDict(use_enum_values=True)
+
+        some_enum: SomeEnum
+        another_enum: Optional[SomeEnum] = Field(default=SomeEnum.FOO, validate_default=True)
+
+
+    model1 = SomeModel(some_enum=SomeEnum.BAR)
+    print(model1.model_dump())
+    # {'some_enum': 'bar', 'another_enum': 'foo'}
+
+    model2 = SomeModel(some_enum=SomeEnum.BAR, another_enum=SomeEnum.BAZ)
+    print(model2.model_dump())
+    #> {'some_enum': 'bar', 'another_enum': 'baz'}
+    ```
     """
 
     validate_assignment: bool

```

</details>

---

## Case 13 — `e77e9fc55d78d6fd`

- **repo** `fastapi/fastapi` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** ➖ Drop support for Python 3.9 (#14897)
- **commit** https://github.com/fastapi/fastapi/commit/ad4e8e006016e088dbccdb73305a58a1338b1ad9
- **doc** `docs/en/docs/tutorial/body-multiple-params.md`
- **code** `fastapi/dependencies/utils.py`
- **shared identifiers** `union`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/tutorial/body-multiple-params.md b/docs/en/docs/tutorial/body-multiple-params.md
index bb0c58368..d904fb839 100644
--- a/docs/en/docs/tutorial/body-multiple-params.md
+++ b/docs/en/docs/tutorial/body-multiple-params.md
@@ -106,13 +106,6 @@ As, by default, singular values are interpreted as query parameters, you don't h
 q: str | None = None
 ```
 
-Or in Python 3.9:
-
-```Python
-q: Union[str, None] = None
-```
-
-
 For example:
 
 {* ../../docs_src/body_multiple_params/tutorial004_an_py310.py hl[28] *}

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/fastapi/dependencies/utils.py b/fastapi/dependencies/utils.py
index 23d8cd9fb..ab18ec2db 100644
--- a/fastapi/dependencies/utils.py
+++ b/fastapi/dependencies/utils.py
@@ -1,18 +1,19 @@
 import dataclasses
 import inspect
 import sys
-from collections.abc import Mapping, Sequence
+from collections.abc import Callable, Mapping, Sequence
 from contextlib import AsyncExitStack, contextmanager
 from copy import copy, deepcopy
 from dataclasses import dataclass
 from typing import (
     Annotated,
     Any,
-    Callable,
     ForwardRef,
-    Optional,
+    Literal,
     Union,
     cast,
+    get_args,
+    get_origin,
 )
 
 from fastapi import params
@@ -63,7 +64,6 @@ from starlette.datastructures import (
 from starlette.requests import HTTPConnection, Request
 from starlette.responses import Response
 from starlette.websockets import WebSocket
-from typing_extensions import Literal, get_args, get_origin
 from typing_inspection.typing_objects import is_typealiastype
 
 multipart_not_installed_error = (
@@ -127,8 +127,8 @@ def get_flat_dependant(
     dependant: Dependant,
     *,
     skip_repeats: bool = False,
-    visited: Optional[list[DependencyCacheKey]] = None,
-    parent_oauth_scopes: Optional[list[str]] = None,
+    visited: list[DependencyCacheKey] | None = None,
+    parent_oauth_scopes: list[str] | None = None,
 ) -> Dependant:
     if visited is None:
         visited = []
@@ -199,20 +199,17 @@ def get_flat_params(dependant: Dependant) -> list[ModelField]:
 
 
 def _get_signature(call: Callable[..., Any]) -> inspect.Signature:
-    if sys.version_info >= (3, 10):
-        try:
-            signature = inspect.signature(call, eval_str=True)
-        except NameError:
-            # Handle type annotations with if TYPE_CHECKING, not used by FastAPI
-            # e.g. dependency return types
-            if sys.version_info >= (3, 14):
-                from annotationlib import Format
-
-                signature = inspect.signature(call, annotation_format=Format.FORWARDREF)
-            else:
-                signature = inspect.signature(call)
-    else:
-        signature = inspect.signature(call)
+    try:
+        signature = inspect.signature(call, eval_str=True)
+    except NameError:
+        # Handle type annotations with if TYPE_CHECKING, not used by FastAPI
+        # e.g. dependency return types
+        if sys.version_info >= (3, 14):
+            from annotationlib import Format
+
+            signature = inspect.signature(call, annotation_format=Format.FORWARDREF)
+        else:
+            signature = inspect.signature(call)
     return signature
 
 
@@ -258,11 +255,11 @@ def get_dependant(
     *,
     path: str,
     call: Callable[..., Any],
-    name: Optional[str] = None,
-    own_oauth_scopes: Optional[list[str]] = None,
-    parent_oauth_scopes: Optional[list[str]] = None,
+    name: str | None = None,
+    own_oauth_scopes: list[str] | None = None,
+    parent_oauth_scopes: list[str] | None = None,
     use_cache: bool = True,
-    scope: Union[Literal["function", "request"], None] = None,
+    scope: Literal["function", "request"] | None = None,
 ) -> Dependant:
     dependant = Dependant(
         call=call,
@@ -331,7 +328,7 @@ def get_dependant(
 
 def add_non_field_param_to_dependency(
     *, param_name: str, type_annotation: Any, dependant: Dependant
-) -> Optional[bool]:
+) -> bool | None:
     if lenient_issubclass(type_annotation, Request):
         dependant.request_param_name = param_name
         return True
@@ -356,8 +353,8 @@ def add_non_field_param_to_dependency(
 @dataclass
 class ParamDetails:
     type_annotation: Any
-    depends: Optional[params.Depends]
-    field: Optional[ModelField]
+    depends: params.Depends | None
+    field: ModelField | None
 
 
 def analyze_param(
@@ -399,7 +396,7 @@ def analyze_param(
             )
         ]
         if fastapi_specific_annotations:
-            fastapi_annotation: Union[FieldInfo, params.Depends, None] = (
+  
```

</details>

---

## Case 14 — `53f5fcdce1efc6fa`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** remove previously deprecated code
- **commit** https://github.com/pallets/flask/commit/6650764e9719402de2aaa6f321bdec587699c6b2
- **doc** `docs/config.rst`
- **code** `src/flask/blueprints.py`
- **shared identifiers** `versionchanged`, `versionadded`, `application`, `deprecated`, `provider`, `ver:2.2`, `ver:2.3`, `flask`, `attr`, `json`

**VERDICT: `unrelated`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/config.rst b/docs/config.rst
index 9db2045f..d71f0326 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -65,18 +65,6 @@ Builtin Configuration Values
 
 The following configuration values are used internally by Flask:
 
-.. py:data:: ENV
-
-    What environment the app is running in. The :attr:`~flask.Flask.env` attribute maps
-    to this config key.
-
-    Default: ``'production'``
-
-    .. deprecated:: 2.2
-        Will be removed in Flask 2.3. Use ``--debug`` instead.
-
-    .. versionadded:: 1.0
-
 .. py:data:: DEBUG
 
     Whether debug mode is enabled. When using ``flask run`` to start the development
@@ -271,52 +259,6 @@ The following configuration values are used internally by Flask:
 
     Default: ``None``
 
-.. py:data:: JSON_AS_ASCII
-
-    Serialize objects to ASCII-encoded JSON. If this is disabled, the
-    JSON returned from ``jsonify`` will contain Unicode characters. This
-    has security implications when rendering the JSON into JavaScript in
-    templates, and should typically remain enabled.
-
-    Default: ``True``
-
-    .. deprecated:: 2.2
-        Will be removed in Flask 2.3. Set ``app.json.ensure_ascii``
-        instead.
-
-.. py:data:: JSON_SORT_KEYS
-
-    Sort the keys of JSON objects alphabetically. This is useful for caching
-    because it ensures the data is serialized the same way no matter what
-    Python's hash seed is. While not recommended, you can disable this for a
-    possible performance improvement at the cost of caching.
-
-    Default: ``True``
-
-    .. deprecated:: 2.2
-        Will be removed in Flask 2.3. Set ``app.json.sort_keys``
-        instead.
-
-.. py:data:: JSONIFY_PRETTYPRINT_REGULAR
-
-    :func:`~flask.jsonify` responses will be output with newlines,
-    spaces, and indentation for easier reading by humans. Always enabled
-    in debug mode.
-
-    Default: ``False``
-
-    .. deprecated:: 2.2
-        Will be removed in Flask 2.3. Set ``app.json.compact`` instead.
-
-.. py:data:: JSONIFY_MIMETYPE
-
-    The mimetype of ``jsonify`` responses.
-
-    Default: ``'application/json'``
-
-    .. deprecated:: 2.2
-        Will be removed in Flask 2.3. Set ``app.json.mimetype`` instead.
-
 .. py:data:: TEMPLATES_AUTO_RELOAD
 
     Reload templates when they are changed. If not set, it will be enabled in
@@ -381,14 +323,13 @@ The following configuration values are used internally by Flask:
 .. versionchanged:: 2.2
     Removed ``PRESERVE_CONTEXT_ON_EXCEPTION``.
 
-.. versionchanged:: 2.2
-    ``JSON_AS_ASCII``, ``JSON_SORT_KEYS``,
-    ``JSONIFY_MIMETYPE``, and ``JSONIFY_PRETTYPRINT_REGULAR`` will be
-    removed in Flask 2.3. The default ``app.json`` provider has
+.. versionchanged:: 2.3
+    ``JSON_AS_ASCII``, ``JSON_SORT_KEYS``, ``JSONIFY_MIMETYPE``, and
+    ``JSONIFY_PRETTYPRINT_REGULAR`` were removed. The default ``app.json`` provider has
     equivalent attributes instead.
 
-.. versionchanged:: 2.2
-    ``ENV`` will be removed in Flask 2.3. Use ``--debug`` instead.
+.. versionchanged:: 2.3
+    ``ENV`` was removed.
 
 
 Configuring from Python Files

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/blueprints.py b/src/flask/blueprints.py
index 4e3fe842..51f72279 100644
--- a/src/flask/blueprints.py
+++ b/src/flask/blueprints.py
@@ -1,4 +1,3 @@
-import json
 import os
 import typing as t
 from collections import defaultdict
@@ -15,9 +14,6 @@ if t.TYPE_CHECKING:  # pragma: no cover
 
 DeferredSetupFunction = t.Callable[["BlueprintSetupState"], t.Callable]
 T_after_request = t.TypeVar("T_after_request", bound=ft.AfterRequestCallable)
-T_before_first_request = t.TypeVar(
-    "T_before_first_request", bound=ft.BeforeFirstRequestCallable
-)
 T_before_request = t.TypeVar("T_before_request", bound=ft.BeforeRequestCallable)
 T_error_handler = t.TypeVar("T_error_handler", bound=ft.ErrorHandlerCallable)
 T_teardown = t.TypeVar("T_teardown", bound=ft.TeardownCallable)
@@ -173,77 +169,6 @@ class Blueprint(Scaffold):
 
     _got_registered_once = False
 
-    _json_encoder: t.Union[t.Type[json.JSONEncoder], None] = None
-    _json_decoder: t.Union[t.Type[json.JSONDecoder], None] = None
-
-    @property
-    def json_encoder(
-        self,
-    ) -> t.Union[t.Type[json.JSONEncoder], None]:
-        """Blueprint-local JSON encoder class to use. Set to ``None`` to use the app's.
-
-        .. deprecated:: 2.2
-             Will be removed in Flask 2.3. Customize
-             :attr:`json_provider_class` instead.
-
-        .. versionadded:: 0.10
-        """
-        import warnings
-
-        warnings.warn(
-            "'bp.json_encoder' is deprecated and will be removed in Flask 2.3."
-            " Customize 'app.json_provider_class' or 'app.json' instead.",
-            DeprecationWarning,
-            stacklevel=2,
-        )
-        return self._json_encoder
-
-    @json_encoder.setter
-    def json_encoder(self, value: t.Union[t.Type[json.JSONEncoder], None]) -> None:
-        import warnings
-
-        warnings.warn(
-            "'bp.json_encoder' is deprecated and will be removed in Flask 2.3."
-            " Customize 'app.json_provider_class' or 'app.json' instead.",
-            DeprecationWarning,
-            stacklevel=2,
-        )
-        self._json_encoder = value
-
-    @property
-    def json_decoder(
-        self,
-    ) -> t.Union[t.Type[json.JSONDecoder], None]:
-        """Blueprint-local JSON decoder class to use. Set to ``None`` to use the app's.
-
-        .. deprecated:: 2.2
-             Will be removed in Flask 2.3. Customize
-             :attr:`json_provider_class` instead.
-
-        .. versionadded:: 0.10
-        """
-        import warnings
-
-        warnings.warn(
-            "'bp.json_decoder' is deprecated and will be removed in Flask 2.3."
-            " Customize 'app.json_provider_class' or 'app.json' instead.",
-            DeprecationWarning,
-            stacklevel=2,
-        )
-        return self._json_decoder
-
-    @json_decoder.setter
-    def json_decoder(self, value: t.Union[t.Type[json.JSONDecoder], None]) -> None:
-        import warnings
-
-        warnings.warn(
-            "'bp.json_decoder' is deprecated and will be removed in Flask 2.3."
-            " Customize 'app.json_provider_class' or 'app.json' instead.",
-            DeprecationWarning,
-            stacklevel=2,
-        )
-        self._json_decoder = value
-
     def __init__(
         self,
         name: str,
@@ -361,6 +286,10 @@ class Blueprint(Scaffold):
         .. versionchanged:: 2.3
             Nested blueprints now correctly apply subdomains.
 
+        .. versionchanged:: 2.1
+            Registering the same blueprint with the same name multiple
+            times is an error.
+
         .. versionchanged:: 2.0.1
             Nested blueprints are registered with their dotted name.
             This allows different blueprints with the same name to be
@@ -371,10 +300,6 @@ class Blueprint(Scaffold):
             name the blueprint is registered with. This allows the same
             blueprint to be registered multiple times with unique names
             for ``url_for``.
-

```

</details>

---

## Case 15 — `6e9e869adb5a9df8`

- **repo** `encode/httpx` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Make charset auto-detection optional. (#2165)
- **commit** https://github.com/encode/httpx/commit/1c33a2854e5d18955c8766c5c01e6229716b5b7a
- **doc** `docs/advanced.md`
- **code** `httpx/_models.py`
- **shared identifiers** `default_encoding`, `autodetection`, `normalizer`, `callable`, `encoding`, `charset`, `content`, `bytes`, `best`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/advanced.md b/docs/advanced.md
index 9d3c388..81623fe 100644
--- a/docs/advanced.md
+++ b/docs/advanced.md
@@ -145,6 +145,88 @@ URL('http://httpbin.org/headers')
 
 For a list of all available client parameters, see the [`Client`](api.md#client) API reference.
 
+---
+
+## Character set encodings and auto-detection
+
+When accessing `response.text`, we need to decode the response bytes into a unicode text representation.
+
+By default `httpx` will use `"charset"` information included in the response `Content-Type` header to determine how the response bytes should be decoded into text.
+
+In cases where no charset information is included on the response, the default behaviour is to assume "utf-8" encoding, which is by far the most widely used text encoding on the internet.
+
+### Using the default encoding
+
+To understand this better let's start by looking at the default behaviour for text decoding...
+
+```python
+import httpx
+# Instantiate a client with the default configuration.
+client = httpx.Client()
+# Using the client...
+response = client.get(...)
+print(response.encoding)  # This will either print the charset given in
+                          # the Content-Type charset, or else "utf-8".
+print(response.text)  # The text will either be decoded with the Content-Type
+                      # charset, or using "utf-8".
+```
+
+This is normally absolutely fine. Most servers will respond with a properly formatted Content-Type header, including a charset encoding. And in most cases where no charset encoding is included, UTF-8 is very likely to be used, since it is so widely adopted.
+
+### Using an explicit encoding
+
+In some cases we might be making requests to a site where no character set information is being set explicitly by the server, but we know what the encoding is. In this case it's best to set the default encoding explicitly on the client.
+
+```python
+import httpx
+# Instantiate a client with a Japanese character set as the default encoding.
+client = httpx.Client(default_encoding="shift-jis")
+# Using the client...
+response = client.get(...)
+print(response.encoding)  # This will either print the charset given in
+                          # the Content-Type charset, or else "shift-jis".
+print(response.text)  # The text will either be decoded with the Content-Type
+                      # charset, or using "shift-jis".
+```
+
+### Using character set auto-detection
+
+In cases where the server is not reliably including character set information, and where we don't know what encoding is being used, we can enable auto-detection to make a best-guess attempt when decoding from bytes to text.
+
+To use auto-detection you need to set the `default_encoding` argument to a callable instead of a string. This callable should be a function which takes the input bytes as an argument and returns the character set to use for decoding those bytes to text.
+
+There are two widely used Python packages which both handle this functionality:
+
+* [`chardet`](https://chardet.readthedocs.io/) - This is a well established package, and is a port of [the auto-detection code in Mozilla](https://www-archive.mozilla.org/projects/intl/chardet.html).
+* [`charset-normalizer`](https://charset-normalizer.readthedocs.io/) - A newer package, motivated by `chardet`, with a different approach.
+
+Let's take a look at installing autodetection using one of these packages...
+
+ ```shell
+$ pip install httpx
+$ pip install chardet
+ ```
+
+Once `chardet` is installed, we can configure a client to use character-set autodetection.
+
+```python
+import httpx
+import chardet
+
+def autodetect(content):
+    return chardet.detect(content).get("encoding")
+
+# Using a client with character-set autodetection enabled.
+client = httpx.Client(default_encoding=autodetect)
+response = client.get(...)
+print(response.encoding)  # This will either print the charset given in
+                          # the Content-Type charset, or else the
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/httpx/_models.py b/httpx/_models.py
index 4f82f01..cff6929 100644
--- a/httpx/_models.py
+++ b/httpx/_models.py
@@ -7,8 +7,6 @@ import urllib.request
 from collections.abc import MutableMapping
 from http.cookiejar import Cookie, CookieJar
 
-import charset_normalizer
-
 from ._content import ByteStream, UnattachedStream, encode_request, encode_response
 from ._decoders import (
     SUPPORTED_DECODERS,
@@ -445,6 +443,7 @@ class Response:
         request: typing.Optional[Request] = None,
         extensions: typing.Optional[dict] = None,
         history: typing.Optional[typing.List["Response"]] = None,
+        default_encoding: typing.Union[str, typing.Callable[[bytes], str]] = "utf-8",
     ):
         self.status_code = status_code
         self.headers = Headers(headers)
@@ -461,6 +460,8 @@ class Response:
         self.is_closed = False
         self.is_stream_consumed = False
 
+        self.default_encoding = default_encoding
+
         if stream is None:
             headers, stream = encode_response(content, text, html, json)
             self._prepare(headers)
@@ -569,14 +570,18 @@ class Response:
 
         * `.encoding = <>` has been set explicitly.
         * The encoding as specified by the charset parameter in the Content-Type header.
-        * The encoding as determined by `charset_normalizer`.
-        * UTF-8.
+        * The encoding as determined by `default_encoding`, which may either be
+          a string like "utf-8" indicating the encoding to use, or may be a callable
+          which enables charset autodetection.
         """
         if not hasattr(self, "_encoding"):
             encoding = self.charset_encoding
             if encoding is None or not is_known_encoding(encoding):
-                encoding = self.apparent_encoding
-            self._encoding = encoding
+                if isinstance(self.default_encoding, str):
+                    encoding = self.default_encoding
+                elif hasattr(self, "_content"):
+                    encoding = self.default_encoding(self._content)
+            self._encoding = encoding or "utf-8"
         return self._encoding
 
     @encoding.setter
@@ -598,19 +603,6 @@ class Response:
 
         return params["charset"].strip("'\"")
 
-    @property
-    def apparent_encoding(self) -> typing.Optional[str]:
-        """
-        Return the encoding, as determined by `charset_normalizer`.
-        """
-        content = getattr(self, "_content", b"")
-        if len(content) < 32:
-            # charset_normalizer will issue warnings if we run it with
-            # fewer bytes than this cutoff.
-            return None
-        match = charset_normalizer.from_bytes(self.content).best()
-        return None if match is None else match.encoding
-
     def _get_content_decoder(self) -> ContentDecoder:
         """
         Returns a decoder instance which can be used to decode the raw byte

```

</details>

---

## Case 16 — `bdc3245f66d5cf46`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Create a GetCoreSchemaHandler class (#5619)
- **commit** https://github.com/pydantic/pydantic/commit/28f4495bed0ac16fcba10014bea43b4a66793ca6
- **doc** `docs/usage/schema.md`
- **code** `pydantic/_internal/_core_metadata.py`
- **shared identifiers** `schema`, `json`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/schema.md b/docs/usage/schema.md
index cf01d61ea..daece2ab4 100644
--- a/docs/usage/schema.md
+++ b/docs/usage/schema.md
@@ -388,7 +388,7 @@ from typing import Any, Dict, List, Type
 from pydantic_core import core_schema
 
 from pydantic import BaseModel
-from pydantic.json_schema import GetJsonSchemaHandler
+from pydantic.annotated import GetCoreSchemaHandler
 
 
 @dataclass
@@ -401,7 +401,7 @@ class CompressedString:
 
     @classmethod
     def __get_pydantic_core_schema__(
-        cls, source: Type[Any], handler: GetJsonSchemaHandler
+        cls, source: Type[Any], handler: GetCoreSchemaHandler
     ) -> core_schema.CoreSchema:
         assert source is CompressedString
         return core_schema.no_info_after_validator_function(
@@ -453,12 +453,13 @@ The process for Annotated metadata is much the same except that you can generall
 
 ```py
 from dataclasses import dataclass
-from typing import Any, Callable, Sequence, Type
+from typing import Any, Sequence, Type
 
 from pydantic_core import core_schema
 from typing_extensions import Annotated
 
 from pydantic import BaseModel, ValidationError
+from pydantic.annotated import GetCoreSchemaHandler
 
 
 @dataclass
@@ -466,7 +467,7 @@ class RestrictCharacters:
     alphabet: Sequence[str]
 
     def __get_pydantic_core_schema__(
-        self, source: Type[Any], handler: Callable[[Any], core_schema.CoreSchema]
+        self, source: Type[Any], handler: GetCoreSchemaHandler
     ) -> core_schema.CoreSchema:
         if not self.alphabet:
             raise ValueError('Alphabet may not be empty')
@@ -515,17 +516,20 @@ So far we have been wrapping the schema, but if you just want to *modify* it or
 To modify the schema first call the handler and then mutate the result:
 
 ```py
-from typing import Any, Callable, Type
+from typing import Any, Type
 
 from pydantic_core import ValidationError, core_schema
 from typing_extensions import Annotated
 
 from pydantic import BaseModel
+from pydantic.annotated import GetCoreSchemaHandler
 
 
 class SmallString:
     def __get_pydantic_core_schema__(
-        self, source: Type[Any], handler: Callable[[Any], core_schema.CoreSchema]
+        self,
+        source: Type[Any],
+        handler: GetCoreSchemaHandler,
     ) -> core_schema.CoreSchema:
         schema = handler(source)
         assert schema['type'] == 'str'
@@ -551,17 +555,18 @@ except ValidationError as e:
 To override the schema completely do not call the handler and return your own `CoreSchema`:
 
 ```py
-from typing import Any, Callable, Type
+from typing import Any, Type
 
 from pydantic_core import ValidationError, core_schema
 from typing_extensions import Annotated
 
 from pydantic import BaseModel
+from pydantic.annotated import GetCoreSchemaHandler
 
 
 class AllowAnySubclass:
     def __get_pydantic_core_schema__(
-        self, source: Type[Any], handler: Callable[[Any], core_schema.CoreSchema]
+        self, source: Type[Any], handler: GetCoreSchemaHandler
     ) -> core_schema.CoreSchema:
         # we can't call handler since it will fail for arbitrary types
         def validate(value: Any) -> Any:

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/_internal/_core_metadata.py b/pydantic/_internal/_core_metadata.py
index fb5910beb..afa880f0c 100644
--- a/pydantic/_internal/_core_metadata.py
+++ b/pydantic/_internal/_core_metadata.py
@@ -8,10 +8,10 @@ from pydantic_core import CoreSchema, core_schema
 
 if typing.TYPE_CHECKING:
     from ..json_schema import JsonSchemaValue
-    from ._json_schema_shared import (
+    from ._schema_generation_shared import (
         CoreSchemaOrField as CoreSchemaOrField,
     )
-    from ._json_schema_shared import (
+    from ._schema_generation_shared import (
         GetJsonSchemaFunction,
         GetJsonSchemaHandler,
     )

```

</details>

---

## Case 17 — `0710cbb509d78b3f`

- **repo** `encode/httpx` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Allow default+override timeout style (#593)
- **commit** https://github.com/encode/httpx/commit/2f54b200deda274fe71ca678419142329111d6f7
- **doc** `docs/advanced.md`
- **code** `httpx/exceptions.py`
- **shared identifiers** `timeoutexception`, `connecttimeout`, `writetimeout`, `pooltimeout`, `readtimeout`, `exception`, `connect`, `timeout`, `pool`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/advanced.md b/docs/advanced.md
index e13ea45..42346d5 100644
--- a/docs/advanced.md
+++ b/docs/advanced.md
@@ -250,83 +250,78 @@ async with httpx.Client(proxies=proxy) as client:
     has not been implemented yet. To use proxies you must pass the proxy
     information at `Client` initialization.
 
-## Timeout fine-tuning
+## Timeout Configuration
 
-HTTPX offers various request timeout management options. Three types of timeouts
-are available: **connect** timeouts, **write** timeouts and **read** timeouts.
+HTTPX is careful to enforce timeouts everywhere by default.
 
-* The **connect timeout** specifies the maximum amount of time to wait until
-a connection to the requested host is established. If HTTPX is unable to connect
-within this time frame, a `ConnectTimeout` exception is raised.
-* The **write timeout** specifies the maximum duration to wait for a chunk of
-data to be sent (for example, a chunk of the request body). If HTTPX is unable
-to send data within this time frame, a `WriteTimeout` exception is raised.
-* The **read timeout** specifies the maximum duration to wait for a chunk of
-data to be received (for example, a chunk of the response body). If HTTPX is
-unable to receive data within this time frame, a `ReadTimeout` exception is raised.
-
-### Setting timeouts
+The default behavior is to raise a `TimeoutException` after 5 seconds of
+network inactivity.
 
-You can set timeouts on two levels:
+### Setting and disabling timeouts
 
-- For a given request:
+You can set timeouts for an individual request:
 
 ```python
-# Using top-level API
-await httpx.get('http://example.com/api/v1/example', timeout=5)
+# Using the top-level API:
+await httpx.get('http://example.com/api/v1/example', timeout=10.0)
 
-# Or, with a client:
+# Using a client instance:
 async with httpx.Client() as client:
-    await client.get("http://example.com/api/v1/example", timeout=5)
+    await client.get("http://example.com/api/v1/example", timeout=10.0)
 ```
 
-- On a client instance, which results in the given `timeout` being used as a default for requests made with this client:
+Or disable timeouts for an individual request:
 
 ```python
-async with httpx.Client(timeout=5) as client:
-    await client.get('http://example.com/api/v1/example')
+# Using the top-level API:
+await httpx.get('http://example.com/api/v1/example', timeout=None)
+
+# Using a client instance:
+async with httpx.Client() as client:
+    await client.get("http://example.com/api/v1/example", timeout=None)
 ```
 
-Besides, you can pass timeouts in two forms:
+### Setting a default timeout on a client
 
-- A number, which sets the read, write and connect timeouts to the same value, as in the examples above.
-- A `Timeout` instance, which allows to define the read, write and connect timeouts independently:
+You can set a timeout on a client instance, which results in the given
+`timeout` being used as the default for requests made with this client:
 
 ```python
-timeout = httpx.Timeout(
-    connect_timeout=5,
-    read_timeout=10,
-    write_timeout=15
-)
-
-resp = await httpx.get('http://example.com/api/v1/example', timeout=timeout)
+client = httpx.Client()              # Use a default 5s timeout everywhere.
+client = httpx.Client(timeout=10.0)  # Use a default 10s timeout everywhere.
+client = httpx.Client(timeout=None)  # Disable all timeouts by default.
 ```
 
-### Default timeouts
-
-By default all types of timeouts are set to 5 second.
+### Fine tuning the configuration
 
-### Disabling timeouts
+HTTPX also allows you to specify the timeout behavior in more fine grained detail.
 
-To disable timeouts, you can pass `None` as a timeout parameter.
-Note that currently this is not supported by the top-level API.
-
-```python
-url = "http://example.com/api/v1/delay/10"
-
-await httpx.get(url, timeout=None)  # Times out after 5s
+There are four different types of timeouts that may occur. These are **connect**,
+**read**, **write**, and **pool** timeou
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/httpx/exceptions.py b/httpx/exceptions.py
index 61710cf..b19669c 100644
--- a/httpx/exceptions.py
+++ b/httpx/exceptions.py
@@ -20,31 +20,31 @@ class HTTPError(Exception):
 # Timeout exceptions...
 
 
-class RequestTimeout(HTTPError):
+class TimeoutException(HTTPError):
     """
     A base class for all timeouts.
     """
 
 
-class ConnectTimeout(RequestTimeout):
+class ConnectTimeout(TimeoutException):
     """
     Timeout while establishing a connection.
     """
 
 
-class ReadTimeout(RequestTimeout):
+class ReadTimeout(TimeoutException):
     """
     Timeout while reading response data.
     """
 
 
-class WriteTimeout(RequestTimeout):
+class WriteTimeout(TimeoutException):
     """
     Timeout while writing request data.
     """
 
 
-class PoolTimeout(RequestTimeout):
+class PoolTimeout(TimeoutException):
     """
     Timeout while waiting to acquire a connection from the pool.
     """

```

</details>

---

## Case 18 — `9d7aefcfca62d2a1`

- **repo** `fastapi/fastapi` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** ♻️ Refactor internals to preserve `APIRouter` and `APIRoute` instances (#15745)
- **commit** https://github.com/fastapi/fastapi/commit/8e1d774cef03ab9e2552c26e850cbfc0c63974c3
- **doc** `docs/en/docs/advanced/openapi-callbacks.md`
- **code** `fastapi/routing.py`
- **shared identifiers** `callbacks`, `operation`, `generate`, `fastapi`, `openapi`, `router`, `routes`, `path`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/advanced/openapi-callbacks.md b/docs/en/docs/advanced/openapi-callbacks.md
index 40cf47956..819709110 100644
--- a/docs/en/docs/advanced/openapi-callbacks.md
+++ b/docs/en/docs/advanced/openapi-callbacks.md
@@ -167,13 +167,13 @@ Notice how the callback URL used contains the URL received as a query parameter
 
 At this point you have the *callback path operation(s)* needed (the one(s) that the *external developer*  should implement in the *external API*) in the callback router you created above.
 
-Now use the parameter `callbacks` in *your API's path operation decorator* to pass the attribute `.routes` (that's actually just a `list` of routes/*path operations*) from that callback router:
+Now use the parameter `callbacks` in *your API's path operation decorator* to pass the attribute `.routes` from that callback router:
 
 {* ../../docs_src/openapi_callbacks/tutorial001_py310.py hl[33] *}
 
 /// tip
 
-Notice that you are not passing the router itself (`invoices_callback_router`) to `callback=`, but the attribute `.routes`, as in `invoices_callback_router.routes`.
+Notice that you are not passing the router itself (`invoices_callback_router`) to `callbacks=`, but its `.routes`, as in `invoices_callback_router.routes`. FastAPI will use those routes to generate the callback OpenAPI documentation.
 
 ///
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/fastapi/routing.py b/fastapi/routing.py
index 21a1385a2..fb4784309 100644
--- a/fastapi/routing.py
+++ b/fastapi/routing.py
@@ -1,4 +1,5 @@
 import contextlib
+import copy
 import email.message
 import functools
 import inspect
@@ -21,10 +22,13 @@ from contextlib import (
     AsyncExitStack,
     asynccontextmanager,
 )
+from contextvars import ContextVar
+from dataclasses import dataclass, field
 from enum import Enum, IntEnum
 from typing import (
     Annotated,
     Any,
+    Protocol,
     TypeVar,
     cast,
 )
@@ -74,12 +78,17 @@ from fastapi.utils import (
 )
 from starlette import routing
 from starlette._exception_handler import wrap_app_handling_exceptions
-from starlette._utils import is_async_callable
+from starlette._utils import get_route_path, is_async_callable
 from starlette.concurrency import iterate_in_threadpool, run_in_threadpool
-from starlette.datastructures import FormData
+from starlette.datastructures import FormData, URLPath
 from starlette.exceptions import HTTPException
 from starlette.requests import Request
-from starlette.responses import JSONResponse, Response, StreamingResponse
+from starlette.responses import (
+    JSONResponse,
+    PlainTextResponse,
+    Response,
+    StreamingResponse,
+)
 from starlette.routing import (
     BaseRoute,
     Match,
@@ -808,6 +817,250 @@ class APIWebSocketRoute(routing.WebSocketRoute):
         return match, child_scope
 
 
+_FASTAPI_SCOPE_KEY = "fastapi"
+_FASTAPI_EFFECTIVE_ROUTE_CONTEXT_KEY = "effective_route_context"
+_FASTAPI_INCLUDED_ROUTER_KEY = "included_router"
+_effective_route_context_var: ContextVar[Any | None] = ContextVar(
+    "fastapi_effective_route_context", default=None
+)
+_SCOPE_MISSING = object()
+
+
+def _get_fastapi_scope(scope: Scope) -> dict[str, Any]:
+    fastapi_scope = scope.setdefault(_FASTAPI_SCOPE_KEY, {})
+    assert isinstance(fastapi_scope, dict)
+    return fastapi_scope
+
+
+def _get_scope_effective_route_context(scope: Scope) -> Any | None:
+    return scope.get(_FASTAPI_SCOPE_KEY, {}).get(_FASTAPI_EFFECTIVE_ROUTE_CONTEXT_KEY)
+
+
+def _get_scope_included_router(scope: Scope) -> Any | None:
+    return scope.get(_FASTAPI_SCOPE_KEY, {}).get(_FASTAPI_INCLUDED_ROUTER_KEY)
+
+
+def _restore_fastapi_scope_key(scope: Scope, key: str, previous: Any) -> None:
+    fastapi_scope = scope.get(_FASTAPI_SCOPE_KEY)
+    if not isinstance(fastapi_scope, dict):
+        return
+    if previous is _SCOPE_MISSING:
+        fastapi_scope.pop(key, None)
+    else:
+        fastapi_scope[key] = previous
+
+
+class _APIRouteLike(Protocol):
+    path: str
+    endpoint: Callable[..., Any]
+    stream_item_type: Any | None
+    response_model: Any
+    summary: str | None
+    response_description: str
+    deprecated: bool | None
+    operation_id: str | None
+    response_model_include: IncEx | None
+    response_model_exclude: IncEx | None
+    response_model_by_alias: bool
+    response_model_exclude_unset: bool
+    response_model_exclude_defaults: bool
+    response_model_exclude_none: bool
+    include_in_schema: bool
+    response_class: type[Response] | DefaultPlaceholder
+    dependency_overrides_provider: Any | None
+    callbacks: list[BaseRoute] | None
+    openapi_extra: dict[str, Any] | None
+    generate_unique_id_function: Callable[[Any], str] | DefaultPlaceholder
+    strict_content_type: bool | DefaultPlaceholder
+    tags: list[str | Enum]
+    responses: dict[int | str, dict[str, Any]]
+    name: str
+    path_regex: Any
+    path_format: str
+    param_convertors: dict[str, Any]
+    methods: set[str]
+    unique_id: str
+    status_code: int | None
+    response_field: ModelField | None
+    stream_item_field: ModelField | None
+    dependencies: list[params.Depends]
+    description: str
+    response_fields: dict[int | str, ModelField]
+    dependant: Dependant
+    _flat_dependant: Dependant
+    _embed_body_fields: bool
+    body_field: ModelField | None
+    is_sse_stream: bool
+    is_json_stream:
```

</details>

---

## Case 19 — `b8761c132646a874`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Allow str as argument to `Discriminator` (#8047)
- **commit** https://github.com/pydantic/pydantic/commit/a9cebd421744557a64437fc6287513a7a24d63fa
- **doc** `docs/concepts/fields.md`
- **code** `pydantic/fields.py`
- **shared identifiers** `callablediscriminator`, `discriminator`, `callable`, `field`, `union`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/concepts/fields.md b/docs/concepts/fields.md
index f1e5cb135..5288960e5 100644
--- a/docs/concepts/fields.md
+++ b/docs/concepts/fields.md
@@ -597,8 +597,8 @@ print(user)
 ## Discriminator
 
 The parameter `discriminator` can be used to control the field that will be used to discriminate between different
-models in a union. It takes either the name of a field or a `CallableDiscriminator` instance. The `CallableDiscriminator`
-approach can be useful when the discriminator fields aren't the same for all of the models in the `Union`.
+models in a union. It takes either the name of a field or a `Discriminator` instance. The `Discriminator`
+approach can be useful when the discriminator fields aren't the same for all the models in the `Union`.
 
 The following example shows how to use `discriminator` with a field name:
 
@@ -628,14 +628,14 @@ print(Model.model_validate({'pet': {'pet_type': 'cat', 'age': 12}}))  # (1)!
 
 1. See more about [Helper Functions] in the [Models] page.
 
-The following example shows how to use `discriminator` with a `CallableDiscriminator` instance:
+The following example shows how to use the `discriminator` keyword argument with a `Discriminator` instance:
 
 ```py requires="3.8"
 from typing import Literal, Union
 
 from typing_extensions import Annotated
 
-from pydantic import BaseModel, CallableDiscriminator, Field, Tag
+from pydantic import BaseModel, Discriminator, Field, Tag
 
 
 class Cat(BaseModel):
@@ -656,7 +656,7 @@ def pet_discriminator(v):
 
 class Model(BaseModel):
     pet: Union[Annotated[Cat, Tag('cat')], Annotated[Dog, Tag('dog')]] = Field(
-        discriminator=CallableDiscriminator(pet_discriminator)
+        discriminator=Discriminator(pet_discriminator)
     )
 
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/fields.py b/pydantic/fields.py
index 731f37b12..6dc71c55c 100644
--- a/pydantic/fields.py
+++ b/pydantic/fields.py
@@ -64,7 +64,7 @@ class _FromFieldInfoInputs(typing_extensions.TypedDict, total=False):
     max_digits: int | None
     decimal_places: int | None
     union_mode: Literal['smart', 'left_to_right'] | None
-    discriminator: str | types.CallableDiscriminator | None
+    discriminator: str | types.Discriminator | None
     json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None
     frozen: bool | None
     validate_default: bool | None
@@ -101,7 +101,7 @@ class FieldInfo(_repr.Representation):
         description: The description of the field.
         examples: List of examples of the field.
         exclude: Whether to exclude the field from the model serialization.
-        discriminator: Field name or CallableDiscriminator for discriminating the type in a tagged union.
+        discriminator: Field name or Discriminator for discriminating the type in a tagged union.
         json_schema_extra: Dictionary of extra JSON schema properties.
         frozen: Whether the field is frozen.
         validate_default: Whether to validate the default value of the field.
@@ -122,7 +122,7 @@ class FieldInfo(_repr.Representation):
     description: str | None
     examples: list[Any] | None
     exclude: bool | None
-    discriminator: str | types.CallableDiscriminator | None
+    discriminator: str | types.Discriminator | None
     json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None
     frozen: bool | None
     validate_default: bool | None
@@ -682,7 +682,7 @@ def Field(  # noqa: C901
     description: str | None = _Unset,
     examples: list[Any] | None = _Unset,
     exclude: bool | None = _Unset,
-    discriminator: str | types.CallableDiscriminator | None = _Unset,
+    discriminator: str | types.Discriminator | None = _Unset,
     json_schema_extra: JsonDict | typing.Callable[[JsonDict], None] | None = _Unset,
     frozen: bool | None = _Unset,
     validate_default: bool | None = _Unset,
@@ -727,7 +727,7 @@ def Field(  # noqa: C901
         description: Human-readable description.
         examples: Example values for this field.
         exclude: Whether to exclude the field from the model serialization.
-        discriminator: Field name or CallableDiscriminator for discriminating the type in a tagged union.
+        discriminator: Field name or Discriminator for discriminating the type in a tagged union.
         json_schema_extra: Any additional JSON schema data for the schema property.
         frozen: Whether the field is frozen.
         validate_default: Run validation that isn't only checking existence of defaults. This can be set to `True` or `False`. If not set, it defaults to `None`.

```

</details>

---

## Case 20 — `f53693cb2afac96b`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** blinker is required, signals are always available
- **commit** https://github.com/pallets/flask/commit/9cb1a7a52d7927071e2b737d52f902f006969e82
- **doc** `docs/appcontext.rst`
- **code** `src/flask/__init__.py`
- **shared identifiers** `signals_available`, `signals`, `flask`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/appcontext.rst b/docs/appcontext.rst
index a4ae3861..5509a9a7 100644
--- a/docs/appcontext.rst
+++ b/docs/appcontext.rst
@@ -140,10 +140,8 @@ Accessing ``db`` will call ``get_db`` internally, in the same way that
 Events and Signals
 ------------------
 
-The application will call functions registered with
-:meth:`~Flask.teardown_appcontext` when the application context is
-popped.
+The application will call functions registered with :meth:`~Flask.teardown_appcontext`
+when the application context is popped.
 
-If :data:`~signals.signals_available` is true, the following signals are
-sent: :data:`appcontext_pushed`, :data:`appcontext_tearing_down`, and
-:data:`appcontext_popped`.
+The following signals are sent: :data:`appcontext_pushed`,
+:data:`appcontext_tearing_down`, and :data:`appcontext_popped`.

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/__init__.py b/src/flask/__init__.py
index 2361bdb4..4441b95a 100644
--- a/src/flask/__init__.py
+++ b/src/flask/__init__.py
@@ -32,7 +32,6 @@ from .signals import message_flashed as message_flashed
 from .signals import request_finished as request_finished
 from .signals import request_started as request_started
 from .signals import request_tearing_down as request_tearing_down
-from .signals import signals_available as signals_available
 from .signals import template_rendered as template_rendered
 from .templating import render_template as render_template
 from .templating import render_template_string as render_template_string
@@ -89,4 +88,15 @@ def __getattr__(name):
         )
         return Markup
 
+    if name == "signals_available":
+        import warnings
+
+        warnings.warn(
+            "'signals_available' is deprecated and will be removed in Flask 2.4."
+            " Signals are always available",
+            DeprecationWarning,
+            stacklevel=2,
+        )
+        return True
+
     raise AttributeError(name)

```

</details>

---

## Case 21 — `3bd0acd22fce95c0`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Simplify the async handling code
- **commit** https://github.com/pallets/flask/commit/7f87f3dd93baf45d5f69f02a2dcf4493dfc4a1be
- **doc** `docs/async-await.rst`
- **code** `src/flask/blueprints.py`
- **shared identifiers** `ensure_sync`, `functions`, `ensure`, `flask`, `meth`, `sync`, `view`

**VERDICT: `unrelated`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/async-await.rst b/docs/async-await.rst
index 23b418de..34751d47 100644
--- a/docs/async-await.rst
+++ b/docs/async-await.rst
@@ -92,6 +92,21 @@ not work with async views because they will not await the function or be
 awaitable. Other functions they provide will not be awaitable either and
 will probably be blocking if called within an async view.
 
+Extension authors can support async functions by utilising the
+:meth:`flask.Flask.ensure_sync` method. For example, if the extension
+provides a view function decorator add ``ensure_sync`` before calling
+the decorated function,
+
+.. code-block:: python
+
+    def extension(func):
+        @wraps(func)
+        def wrapper(*args, **kwargs):
+            ...  # Extension logic
+            return current_app.ensure_sync(func)(*args, **kwargs)
+
+        return wrapper
+
 Check the changelog of the extension you want to use to see if they've
 implemented async support, or make a feature request or PR to them.
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/blueprints.py b/src/flask/blueprints.py
index a2b6c0f5..5fb84d86 100644
--- a/src/flask/blueprints.py
+++ b/src/flask/blueprints.py
@@ -292,13 +292,10 @@ class Blueprint(Scaffold):
         # Merge blueprint data into parent.
         if first_registration:
 
-            def extend(bp_dict, parent_dict, ensure_sync=False):
+            def extend(bp_dict, parent_dict):
                 for key, values in bp_dict.items():
                     key = self.name if key is None else f"{self.name}.{key}"
 
-                    if ensure_sync:
-                        values = [app.ensure_sync(func) for func in values]
-
                     parent_dict[key].extend(values)
 
             for key, value in self.error_handler_spec.items():
@@ -307,8 +304,7 @@ class Blueprint(Scaffold):
                     dict,
                     {
                         code: {
-                            exc_class: app.ensure_sync(func)
-                            for exc_class, func in code_values.items()
+                            exc_class: func for exc_class, func in code_values.items()
                         }
                         for code, code_values in value.items()
                     },
@@ -316,16 +312,13 @@ class Blueprint(Scaffold):
                 app.error_handler_spec[key] = value
 
             for endpoint, func in self.view_functions.items():
-                app.view_functions[endpoint] = app.ensure_sync(func)
+                app.view_functions[endpoint] = func
 
-            extend(
-                self.before_request_funcs, app.before_request_funcs, ensure_sync=True
-            )
-            extend(self.after_request_funcs, app.after_request_funcs, ensure_sync=True)
+            extend(self.before_request_funcs, app.before_request_funcs)
+            extend(self.after_request_funcs, app.after_request_funcs)
             extend(
                 self.teardown_request_funcs,
                 app.teardown_request_funcs,
-                ensure_sync=True,
             )
             extend(self.url_default_functions, app.url_default_functions)
             extend(self.url_value_preprocessors, app.url_value_preprocessors)
@@ -478,9 +471,7 @@ class Blueprint(Scaffold):
         before each request, even if outside of a blueprint.
         """
         self.record_once(
-            lambda s: s.app.before_request_funcs.setdefault(None, []).append(
-                s.app.ensure_sync(f)
-            )
+            lambda s: s.app.before_request_funcs.setdefault(None, []).append(f)
         )
         return f
 
@@ -490,9 +481,7 @@ class Blueprint(Scaffold):
         """Like :meth:`Flask.before_first_request`.  Such a function is
         executed before the first request to the application.
         """
-        self.record_once(
-            lambda s: s.app.before_first_request_funcs.append(s.app.ensure_sync(f))
-        )
+        self.record_once(lambda s: s.app.before_first_request_funcs.append(f))
         return f
 
     def after_app_request(self, f: AfterRequestCallable) -> AfterRequestCallable:
@@ -500,9 +489,7 @@ class Blueprint(Scaffold):
         is executed after each request, even if outside of the blueprint.
         """
         self.record_once(
-            lambda s: s.app.after_request_funcs.setdefault(None, []).append(
-                s.app.ensure_sync(f)
-            )
+            lambda s: s.app.after_request_funcs.setdefault(None, []).append(f)
         )
         return f
 
@@ -553,14 +540,3 @@ class Blueprint(Scaffold):
             lambda s: s.app.url_default_functions.setdefault(None, []).append(f)
         )
         return f
-
-    def ensure_sync(self, f: t.Callable) -> t.Callable:
-        """Ensure the function is synchronous.
-
-        Override if you would like custom async to sync behaviour in
-        this blueprint. Otherwise the app's
-        :meth:`~flask.Flask.ensure_sync` is used.
-
-        .. versionadded:: 2.0
-        """
-        return f

```

</details>

---

## Case 22 — `bc49a74f1620e70a`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Eliminate the undefined types warning (#5754)
- **commit** https://github.com/pydantic/pydantic/commit/67396b3843d7b8fd2783c3b8f7077e5e6e218b9f
- **doc** `docs/usage/types/custom.md`
- **code** `pydantic/_internal/_model_construction.py`
- **shared identifiers** `undefined_types_warning`, `model_rebuild`, `undefined`, `pydantic`, `defined`, `rebuild`, `config`, `model`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/types/custom.md b/docs/usage/types/custom.md
index 8012e2860..f5f8e0cad 100644
--- a/docs/usage/types/custom.md
+++ b/docs/usage/types/custom.md
@@ -144,58 +144,6 @@ print(type(model2.pet))
 #> <class '__main__.Pet'>
 ```
 
-### Undefined Types Warning
-
-You can suppress the Undefined Types Warning by setting `undefined_types_warning` to `False` in the
-[Model Config](../model_config.md).
-
-```py test="xfail - what do we do with undefined_types_warning?"
-from __future__ import annotations
-
-from pydantic import BaseModel
-
-# This example shows how Book and Person types reference each other.
-# We will demonstrate how to suppress the undefined types warning
-# when define such models.
-
-
-class Book(BaseModel):
-    title: str
-    author: Person  # note the `Person` type is not yet defined
-
-    # Suppress undefined types warning so we can continue defining our models.
-    class Config:
-        undefined_types_warning = False
-
-
-class Person(BaseModel):
-    name: str
-    books_read: list[Book] | None = None
-
-
-# Now, we can rebuild the `Book` model, since the `Person` model is now defined.
-# Note: there's no need to call `model_rebuild()` on `Person`,
-# it's already complete.
-Book.model_rebuild()
-
-# Let's create some instances of our models, to demonstrate that they work.
-python_crash_course = Book(
-    title='Python Crash Course',
-    author=Person(name='Eric Matthes'),
-)
-jane_doe = Person(name='Jane Doe', books_read=[python_crash_course])
-
-assert jane_doe.dict(exclude_unset=True) == {
-    'name': 'Jane Doe',
-    'books_read': [
-        {
-            'title': 'Python Crash Course',
-            'author': {'name': 'Eric Matthes'},
-        },
-    ],
-}
-```
-
 ### Generic Classes as Types
 
 !!! warning

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/_internal/_model_construction.py b/pydantic/_internal/_model_construction.py
index bf673bceb..7fba611b0 100644
--- a/pydantic/_internal/_model_construction.py
+++ b/pydantic/_internal/_model_construction.py
@@ -182,20 +182,19 @@ def complete_model_class(
     except PydanticUndefinedAnnotation as e:
         if raise_errors:
             raise
-        if config_wrapper.undefined_types_warning:
-            config_warning_string = (
-                f'`{cls_name}` has an undefined annotation: `{e.name}`. '
-                f'It may be possible to resolve this by setting '
-                f'undefined_types_warning=False in the config for `{cls_name}`.'
-            )
-            # FIXME UserWarning should not be raised here, but rather warned!
-            raise UserWarning(config_warning_string)
         usage_warning_string = (
             f'`{cls_name}` is not fully defined; you should define `{e.name}`, then call `{cls_name}.model_rebuild()` '
             f'before the first `{cls_name}` instance is created.'
         )
+
+        def attempt_rebuild() -> SchemaValidator | None:
+            if cls.model_rebuild(raise_errors=False, _parent_namespace_depth=0):
+                return cls.__pydantic_validator__
+            else:
+                return None
+
         cls.__pydantic_validator__ = MockValidator(  # type: ignore[assignment]
-            usage_warning_string, code='model-not-fully-defined'
+            usage_warning_string, code='model-not-fully-defined', attempt_rebuild=attempt_rebuild
         )
         return False
 
@@ -294,14 +293,29 @@ class MockValidator:
     Mocker for `pydantic_core.SchemaValidator` which just raises an error when one of its methods is accessed.
     """
 
-    __slots__ = '_error_message', '_code'
-
-    def __init__(self, error_message: str, *, code: PydanticErrorCodes) -> None:
+    __slots__ = '_error_message', '_code', '_attempt_rebuild'
+
+    def __init__(
+        self,
+        error_message: str,
+        *,
+        code: PydanticErrorCodes,
+        attempt_rebuild: Callable[[], SchemaValidator | None] | None = None,
+    ) -> None:
+        """
+        Attempt rebuild
+        """
         self._error_message = error_message
         self._code: PydanticErrorCodes = code
+        self._attempt_rebuild = attempt_rebuild
 
     def __getattr__(self, item: str) -> None:
         __tracebackhide__ = True
+        if self._attempt_rebuild:
+            validator = self._attempt_rebuild()
+            if validator is not None:
+                return getattr(validator, item)
+
         # raise an AttributeError if `item` doesn't exist
         getattr(SchemaValidator, item)
         raise PydanticUserError(self._error_message, code=self._code)

```

</details>

---

## Case 23 — `8ceee7907a82cb40`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Support complex number (#9654)
- **commit** https://github.com/pydantic/pydantic/commit/58abc3dfbea80f5dfc9f83e53f3f31b0e5317f46
- **doc** `docs/errors/validation_errors.md`
- **code** `pydantic/_internal/_generate_schema.py`
- **shared identifiers** `complex`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/errors/validation_errors.md b/docs/errors/validation_errors.md
index 30fac4339..e3ef9e01a 100644
--- a/docs/errors/validation_errors.md
+++ b/docs/errors/validation_errors.md
@@ -198,6 +198,47 @@ except ValidationError as exc:
     #> 'callable_type'
 ```
 
+## `complex_str_parsing`
+
+This error is raised when the input value is a string but cannot be parsed as a complex number because
+it does not follow the [rule](https://docs.python.org/3/library/functions.html#complex) in Python:
+
+```py
+from pydantic import BaseModel, ValidationError
+
+
+class Model(BaseModel):
+    num: complex
+
+
+try:
+    # Complex numbers in json are expected to be valid complex strings.
+    # This value `abc` is not a valid complex string.
+    Model.model_validate_json('{"num": "abc"}')
+except ValidationError as exc:
+    print(repr(exc.errors()[0]['type']))
+    #> 'complex_str_parsing'
+```
+
+## `complex_type`
+
+This error is raised when the input value cannot be interpreted as a complex number:
+
+```py
+from pydantic import BaseModel, ValidationError
+
+
+class Model(BaseModel):
+    num: complex
+
+
+try:
+    Model(num=False)
+except ValidationError as exc:
+    print(repr(exc.errors()[0]['type']))
+    #> 'complex_type'
+```
+
 ## `dataclass_exact_type`
 
 This error is raised when validating a dataclass with `strict=True` and the input is not an instance of the dataclass:

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/_internal/_generate_schema.py b/pydantic/_internal/_generate_schema.py
index 1bede71ca..47f082e2c 100644
--- a/pydantic/_internal/_generate_schema.py
+++ b/pydantic/_internal/_generate_schema.py
@@ -946,6 +946,8 @@ class GenerateSchema:
             return core_schema.float_schema()
         elif obj is bool:
             return core_schema.bool_schema()
+        elif obj is complex:
+            return core_schema.complex_schema()
         elif obj is Any or obj is object:
             return core_schema.any_schema()
         elif obj is datetime.date:

```

</details>

---

## Case 24 — `a753733e2b4c4135`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** request_init -> before_request and request_shutdown -> after_request
- **commit** https://github.com/pallets/flask/commit/fb2d2e446bdd806ea3de7b869c7371e2dae57a23
- **doc** `docs/tutorial.rst`
- **code** `flask.py`
- **shared identifiers** `request_shutdown`, `before_request`, `after_request`, `request_init`, `functions`, `shutdown`, `after`, `init`, `meth`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/tutorial.rst b/docs/tutorial.rst
index bdd624c0..f642423f 100644
--- a/docs/tutorial.rst
+++ b/docs/tutorial.rst
@@ -225,21 +225,21 @@ but how can we elegantly do that for requests?  We will need the database
 connection in all our functions so it makes sense to initialize them
 before each request and shut them down afterwards.
 
-Flask allows us to do that with the :meth:`~flask.Flask.request_init` and
-:meth:`~flask.Flask.request_shutdown` decorators::
+Flask allows us to do that with the :meth:`~flask.Flask.before_request` and
+:meth:`~flask.Flask.after_request` decorators::
 
-    @app.request_init
+    @app.before_request
     def before_request():
         g.db = connect_db()
 
-    @app.request_shutdown
+    @app.after_request
     def after_request(response):
         g.db.close()
         return response
 
-Functions marked with :meth:`~flask.Flask.request_init` are called before
+Functions marked with :meth:`~flask.Flask.before_request` are called before
 a request and passed no arguments, functions marked with
-:meth:`~flask.Flask.request_shutdown` are called after a request and
+:meth:`~flask.Flask.after_request` are called after a request and
 passed the response that will be sent to the client.  They have to return
 that response object or a different one.  In this case we just return it
 unchanged.
@@ -255,7 +255,7 @@ Step 5: The View Functions
 --------------------------
 
 Now that the database connections are working we can start writing the
-view functions.  We will need for of them:
+view functions.  We will need four of them:
 
 Show Entries
 ````````````

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask.py b/flask.py
index ad62e947..f7ba22e6 100644
--- a/flask.py
+++ b/flask.py
@@ -249,16 +249,16 @@ class Flask(object):
         #: of the request before request dispatching kicks in.  This
         #: can for example be used to open database connections or
         #: getting hold of the currently logged in user.
-        #: To register a function here, use the :meth:`request_init`
+        #: To register a function here, use the :meth:`before_request`
         #: decorator.
-        self.request_init_funcs = []
+        self.before_request_funcs = []
 
         #: a list of functions that are called at the end of the
         #: request.  Tha function is passed the current response
         #: object and modify it in place or replace it.
-        #: To register a function here use the :meth:`request_shtdown`
+        #: To register a function here use the :meth:`after_request`
         #: decorator.
-        self.request_shutdown_funcs = []
+        self.after_request_funcs = []
 
         #: a list of functions that are called without arguments
         #: to populate the template context.  Each returns a dictionary
@@ -509,14 +509,14 @@ class Flask(object):
             return f
         return decorator
 
-    def request_init(self, f):
+    def before_request(self, f):
         """Registers a function to run before each request."""
-        self.request_init_funcs.append(f)
+        self.before_request_funcs.append(f)
         return f
 
-    def request_shutdown(self, f):
+    def after_request(self, f):
         """Register a function to be run after each request."""
-        self.request_shutdown_funcs.append(f)
+        self.after_request_funcs.append(f)
         return f
 
     def context_processor(self, f):
@@ -583,19 +583,20 @@ class Flask(object):
 
     def preprocess_request(self):
         """Called before the actual request dispatching and will
-        call every as :func:`request_init` decorated function.
+        call every as :meth:`before_request` decorated function.
         If any of these function returns a value it's handled as
         if it was the return value from the view and further
         request handling is stopped.
         """
-        for func in self.request_init_funcs:
+        for func in self.before_request_funcs:
             rv = func()
             if rv is not None:
                 return rv
 
     def process_response(self, response):
         """Can be overridden in order to modify the response object
-        before it's sent to the WSGI server.
+        before it's sent to the WSGI server.  By default this will
+        call all the :meth:`after_request` decorated functions.
 
         :param response: a :attr:`response_class` object.
         :return: a new response object or the same, has to be an
@@ -604,7 +605,7 @@ class Flask(object):
         session = _request_ctx_stack.top.session
         if session is not None:
             self.save_session(session, response)
-        for handler in self.request_shutdown_funcs:
+        for handler in self.after_request_funcs:
             response = handler(response)
         return response
 

```

</details>

---

## Case 25 — `7478e871321329ec`

- **repo** `fastapi/fastapi` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** 👷‍♀️ Add script for GitHub Topic Repositories and update External Links (#13135)
- **commit** https://github.com/fastapi/fastapi/commit/1b8f823a0559ff36d49e6c724f7c9289f8c10a1f
- **doc** `docs/en/docs/external-links.md`
- **code** `docs/en/docs/js/custom.js`
- **shared identifiers** `html_url`, `projects`, `fastapi`, `target`, `blank`, `login`, `owner`, `topic`, `href`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/external-links.md b/docs/en/docs/external-links.md
index 5a3b8ee33..3ed04e5c5 100644
--- a/docs/en/docs/external-links.md
+++ b/docs/en/docs/external-links.md
@@ -28,9 +28,12 @@ If you have an article, project, tool, or anything related to **FastAPI** that i
 {% endfor %}
 {% endfor %}
 
-## Projects
+## GitHub Repositories
 
-Latest GitHub projects with the topic `fastapi`:
+Most starred GitHub repositories with the topic `fastapi`:
 
-<div class="github-topic-projects">
-</div>
+{% for repo in topic_repos %}
+
+<a href={{repo.html_url}} target="_blank">★ {{repo.stars}} - {{repo.name}}</a> by <a href={{repo.owner_html_url}} target="_blank">@{{repo.owner_login}}</a>.
+
+{% endfor %}

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/docs/en/docs/js/custom.js b/docs/en/docs/js/custom.js
index ff17710e2..4c0ada312 100644
--- a/docs/en/docs/js/custom.js
+++ b/docs/en/docs/js/custom.js
@@ -1,25 +1,3 @@
-const div = document.querySelector('.github-topic-projects')
-
-async function getDataBatch(page) {
-    const response = await fetch(`https://api.github.com/search/repositories?q=topic:fastapi&per_page=100&page=${page}`, { headers: { Accept: 'application/vnd.github.mercy-preview+json' } })
-    const data = await response.json()
-    return data
-}
-
-async function getData() {
-    let page = 1
-    let data = []
-    let dataBatch = await getDataBatch(page)
-    data = data.concat(dataBatch.items)
-    const totalCount = dataBatch.total_count
-    while (data.length < totalCount) {
-        page += 1
-        dataBatch = await getDataBatch(page)
-        data = data.concat(dataBatch.items)
-    }
-    return data
-}
-
 function setupTermynal() {
     document.querySelectorAll(".use-termynal").forEach(node => {
         node.style.display = "block";
@@ -158,20 +136,6 @@ async function showRandomAnnouncement(groupId, timeInterval) {
 }
 
 async function main() {
-    if (div) {
-        data = await getData()
-        div.innerHTML = '<ul></ul>'
-        const ul = document.querySelector('.github-topic-projects ul')
-        data.forEach(v => {
-            if (v.full_name === 'fastapi/fastapi') {
-                return
-            }
-            const li = document.createElement('li')
-            li.innerHTML = `<a href="${v.html_url}" target="_blank">★ ${v.stargazers_count} - ${v.full_name}</a> by <a href="${v.owner.html_url}" target="_blank">@${v.owner.login}</a>`
-            ul.append(li)
-        })
-    }
-
     setupTermynal();
     showRandomAnnouncement('announce-left', 5000)
     showRandomAnnouncement('announce-right', 10000)

```

</details>

---

