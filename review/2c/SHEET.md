# Doc -> code relevance — stage 2c

**The question, for each document:** which code files does this document make claims
about? A claim is any assertion about behaviour, signature, defaults or errors that
could be checked against the code and could one day be wrong about it.

Mark a file by putting an `x` in its box: `- [x] src/flask/app.py`

Rules that matter for the measurement:

- **Mark every file the doc makes claims about, not the best one.** There is no cap.
- **Do not guess.** If you cannot tell without reading the code, read the code — every
  candidate file is written out next to the doc.
- **If the doc makes no claim about any specific file, mark `NONE`.** An install guide
  or a contributing note is a real answer, not a skipped case.
- **The checklist is not a limit.** Anything missing goes on the `EXTRA` line.
- **Leave a case entirely unmarked to skip it.** Partial sheets score fine: results
  are reported per repo and per case count, never pooled into one number.

Nothing here was suggested by a ranker. The candidate list is the repository tree at
one commit, in path order.


18 documents, seed 20260918.

---

## Case 1 — `encode/httpx` · `docs/advanced/authentication.md`

- **read** `review/2c/text/encode-httpx/doc/docs-advanced-authentication.md` (8554 chars)
- **code** `review/2c/text/encode-httpx/code`
- **tree** `b5addb64f016`

- [ ] httpx/__init__.py
- [ ] httpx/__version__.py
- [ ] httpx/_api.py
- [x] httpx/_auth.py
- [x] httpx/_client.py
- [ ] httpx/_config.py
- [ ] httpx/_content.py
- [ ] httpx/_decoders.py
- [ ] httpx/_exceptions.py
- [ ] httpx/_main.py
- [x] httpx/_models.py
- [ ] httpx/_multipart.py
- [ ] httpx/_status_codes.py
- [ ] httpx/_transports/__init__.py
- [ ] httpx/_transports/asgi.py
- [ ] httpx/_transports/base.py
- [ ] httpx/_transports/default.py
- [ ] httpx/_transports/mock.py
- [ ] httpx/_transports/wsgi.py
- [ ] httpx/_types.py
- [ ] httpx/_urlparse.py
- [ ] httpx/_urls.py
- [ ] httpx/_utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** auth classes+auth_flow in _auth.py; auth= arg on Client/AsyncClient in _client.py; request.headers/content, response.json/content/status_code in _models.py.
---

## Case 2 — `encode/httpx` · `docs/advanced/extensions.md`

- **read** `review/2c/text/encode-httpx/doc/docs-advanced-extensions.md` (9446 chars)
- **code** `review/2c/text/encode-httpx/code`
- **tree** `b5addb64f016`

- [ ] httpx/__init__.py
- [ ] httpx/__version__.py
- [ ] httpx/_api.py
- [ ] httpx/_auth.py
- [x] httpx/_client.py
- [ ] httpx/_config.py
- [ ] httpx/_content.py
- [ ] httpx/_decoders.py
- [ ] httpx/_exceptions.py
- [ ] httpx/_main.py
- [x] httpx/_models.py
- [ ] httpx/_multipart.py
- [ ] httpx/_status_codes.py
- [ ] httpx/_transports/__init__.py
- [ ] httpx/_transports/asgi.py
- [ ] httpx/_transports/base.py
- [x] httpx/_transports/default.py
- [ ] httpx/_transports/mock.py
- [ ] httpx/_transports/wsgi.py
- [ ] httpx/_types.py
- [ ] httpx/_urlparse.py
- [ ] httpx/_urls.py
- [ ] httpx/_utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** request/response .extensions live on Request/Response (_models.py); extension plumbing in _client.py; trace/sni_hostname/target reach the transport (_transports/default.py). timeout extension relates to _config.py but the doc says use the high-level timeout API, so not marked here.
---

## Case 3 — `encode/httpx` · `docs/advanced/timeouts.md`

- **read** `review/2c/text/encode-httpx/doc/docs-advanced-timeouts.md` (2763 chars)
- **code** `review/2c/text/encode-httpx/code`
- **tree** `b5addb64f016`

- [ ] httpx/__init__.py
- [ ] httpx/__version__.py
- [x] httpx/_api.py
- [ ] httpx/_auth.py
- [x] httpx/_client.py
- [x] httpx/_config.py
- [ ] httpx/_content.py
- [ ] httpx/_decoders.py
- [x] httpx/_exceptions.py
- [ ] httpx/_main.py
- [ ] httpx/_models.py
- [ ] httpx/_multipart.py
- [ ] httpx/_status_codes.py
- [ ] httpx/_transports/__init__.py
- [ ] httpx/_transports/asgi.py
- [ ] httpx/_transports/base.py
- [ ] httpx/_transports/default.py
- [ ] httpx/_transports/mock.py
- [ ] httpx/_transports/wsgi.py
- [ ] httpx/_types.py
- [ ] httpx/_urlparse.py
- [ ] httpx/_urls.py
- [ ] httpx/_utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** Timeout class + connect/read/write/pool in _config.py; TimeoutException/ConnectTimeout/ReadTimeout/WriteTimeout/PoolTimeout in _exceptions.py; timeout= default on Client (_client.py) and top-level get/request (_api.py).
---

## Case 4 — `encode/httpx` · `docs/api.md`

- **read** `review/2c/text/encode-httpx/doc/docs-api.md` (4484 chars)
- **code** `review/2c/text/encode-httpx/code`
- **tree** `b5addb64f016`

- [ ] httpx/__init__.py
- [ ] httpx/__version__.py
- [x] httpx/_api.py
- [ ] httpx/_auth.py
- [x] httpx/_client.py
- [x] httpx/_config.py
- [ ] httpx/_content.py
- [ ] httpx/_decoders.py
- [ ] httpx/_exceptions.py
- [ ] httpx/_main.py
- [x] httpx/_models.py
- [ ] httpx/_multipart.py
- [ ] httpx/_status_codes.py
- [ ] httpx/_transports/__init__.py
- [ ] httpx/_transports/asgi.py
- [ ] httpx/_transports/base.py
- [ ] httpx/_transports/default.py
- [ ] httpx/_transports/mock.py
- [ ] httpx/_transports/wsgi.py
- [ ] httpx/_types.py
- [ ] httpx/_urlparse.py
- [x] httpx/_urls.py
- [ ] httpx/_utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** Helper funcs request/get/... in _api.py; Client/AsyncClient members in _client.py; Response/Request/Headers/Cookies in _models.py; URL in _urls.py; Proxy in _config.py.
---

## Case 5 — `encode/httpx` · `docs/compatibility.md`

- **read** `review/2c/text/encode-httpx/doc/docs-compatibility.md` (9891 chars)
- **code** `review/2c/text/encode-httpx/code`
- **tree** `b5addb64f016`

- [ ] httpx/__init__.py
- [ ] httpx/__version__.py
- [x] httpx/_api.py
- [ ] httpx/_auth.py
- [x] httpx/_client.py
- [ ] httpx/_config.py
- [x] httpx/_content.py
- [x] httpx/_decoders.py
- [x] httpx/_exceptions.py
- [ ] httpx/_main.py
- [x] httpx/_models.py
- [ ] httpx/_multipart.py
- [x] httpx/_status_codes.py
- [ ] httpx/_transports/__init__.py
- [ ] httpx/_transports/asgi.py
- [ ] httpx/_transports/base.py
- [ ] httpx/_transports/default.py
- [ ] httpx/_transports/mock.py
- [ ] httpx/_transports/wsgi.py
- [ ] httpx/_types.py
- [ ] httpx/_urlparse.py
- [x] httpx/_urls.py
- [ ] httpx/_utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** follow_redirects default + mounts + cookies-on-client + build_request/send in _client.py; response.url->URL in _urls.py/_models.py; next_request in _client.py/_models.py; content= vs data= + deprecation in _content.py; response encoding guess in _decoders.py/_models.py (note: 'charset_normalizer'/'latin1' strings absent from this pinned tree, but the encoding behavior lives there); is_success/no is_ok + codes in _status_codes.py/_models.py; HTTPError hierarchy in _exceptions.py; GET/DELETE/HEAD/OPTIONS no-body + top-level request in _api.py.
---

## Case 6 — `encode/httpx` · `docs/logging.md`

- **read** `review/2c/text/encode-httpx/doc/docs-logging.md` (3962 chars)
- **code** `review/2c/text/encode-httpx/code`
- **tree** `b5addb64f016`

- [ ] httpx/__init__.py
- [ ] httpx/__version__.py
- [ ] httpx/_api.py
- [ ] httpx/_auth.py
- [x] httpx/_client.py
- [ ] httpx/_config.py
- [ ] httpx/_content.py
- [ ] httpx/_decoders.py
- [ ] httpx/_exceptions.py
- [ ] httpx/_main.py
- [ ] httpx/_models.py
- [ ] httpx/_multipart.py
- [ ] httpx/_status_codes.py
- [ ] httpx/_transports/__init__.py
- [ ] httpx/_transports/asgi.py
- [ ] httpx/_transports/base.py
- [ ] httpx/_transports/default.py
- [ ] httpx/_transports/mock.py
- [ ] httpx/_transports/wsgi.py
- [ ] httpx/_types.py
- [ ] httpx/_urlparse.py
- [ ] httpx/_urls.py
- [ ] httpx/_utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** Only concrete code claim is the 'httpx' logger emitting INFO 'HTTP Request: ...' — getLogger + that line are in _client.py. The 'httpcore' logger is a separate package (not in pool).
---

## Case 7 — `psf/requests` · `README.md`

- **read** `review/2c/text/psf-requests/doc/README.md` (2894 chars)
- **code** `review/2c/text/psf-requests/code`
- **tree** `dae7ef63b4df`

- [ ] docs/_themes/flask_theme_support.py
- [ ] docs/conf.py
- [x] setup.py
- [ ] src/requests/__init__.py
- [ ] src/requests/__version__.py
- [ ] src/requests/_internal_utils.py
- [ ] src/requests/_types.py
- [ ] src/requests/adapters.py
- [x] src/requests/api.py
- [x] src/requests/auth.py
- [ ] src/requests/certs.py
- [ ] src/requests/compat.py
- [ ] src/requests/cookies.py
- [ ] src/requests/exceptions.py
- [ ] src/requests/help.py
- [ ] src/requests/hooks.py
- [x] src/requests/models.py
- [ ] src/requests/packages.py
- [ ] src/requests/sessions.py
- [ ] src/requests/status_codes.py
- [ ] src/requests/structures.py
- [ ] src/requests/utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** Quickstart: requests.get(...) top-level API (api.py); auth=('user','pass') tuple -> HTTPBasicAuth wiring (auth.py, applied in models.py); r.status_code/.headers/.encoding/.text/.json() (models.py). 'officially supports Python 3.10+' is a setup.py python_requires claim. Feature bullet-list is marketing prose, not file-specific.
---

## Case 8 — `psf/requests` · `docs/community/faq.rst`

- **read** `review/2c/text/psf-requests/doc/docs-community-faq.rst` (3745 chars)
- **code** `review/2c/text/psf-requests/code`
- **tree** `dae7ef63b4df`

- [ ] docs/_themes/flask_theme_support.py
- [ ] docs/conf.py
- [ ] setup.py
- [ ] src/requests/__init__.py
- [ ] src/requests/__version__.py
- [ ] src/requests/_internal_utils.py
- [ ] src/requests/_types.py
- [ ] src/requests/adapters.py
- [ ] src/requests/api.py
- [ ] src/requests/auth.py
- [ ] src/requests/certs.py
- [ ] src/requests/compat.py
- [ ] src/requests/cookies.py
- [ ] src/requests/exceptions.py
- [ ] src/requests/help.py
- [ ] src/requests/hooks.py
- [x] src/requests/models.py
- [ ] src/requests/packages.py
- [ ] src/requests/sessions.py
- [ ] src/requests/status_codes.py
- [ ] src/requests/structures.py
- [x] src/requests/utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** 'automatically decompresses gzip / decodes to unicode / decodes Brotli when installed' -> response content decoding lives in models.py (with utils.py helpers). 'override User-Agent' -> default_user_agent in utils.py. (Brotli string not present in this pinned tree, but the decode behavior is here.) Python 2/3 support prose is a version claim, not marked to a module.
---

## Case 9 — `psf/requests` · `docs/community/recommended.rst`

- **read** `review/2c/text/psf-requests/doc/docs-community-recommended.rst` (2174 chars)
- **code** `review/2c/text/psf-requests/code`
- **tree** `dae7ef63b4df`

- [ ] docs/_themes/flask_theme_support.py
- [ ] docs/conf.py
- [ ] setup.py
- [ ] src/requests/__init__.py
- [ ] src/requests/__version__.py
- [ ] src/requests/_internal_utils.py
- [ ] src/requests/_types.py
- [ ] src/requests/adapters.py
- [ ] src/requests/api.py
- [ ] src/requests/auth.py
- [ ] src/requests/certs.py
- [ ] src/requests/compat.py
- [ ] src/requests/cookies.py
- [ ] src/requests/exceptions.py
- [ ] src/requests/help.py
- [ ] src/requests/hooks.py
- [ ] src/requests/models.py
- [ ] src/requests/packages.py
- [ ] src/requests/sessions.py
- [ ] src/requests/status_codes.py
- [ ] src/requests/structures.py
- [ ] src/requests/utils.py

**NONE:** [x]

**EXTRA:**

**NOTES:** Recommends third-party packages (Certifi, CacheControl, Requests-Toolbelt, requests-oauthlib, Betamax). Makes no checkable claim about requests' own code behavior/signatures. NONE.
---

## Case 10 — `psf/requests` · `docs/dev/contributing.rst`

- **read** `review/2c/text/psf-requests/doc/docs-dev-contributing.rst` (6584 chars)
- **code** `review/2c/text/psf-requests/code`
- **tree** `dae7ef63b4df`

- [ ] docs/_themes/flask_theme_support.py
- [ ] docs/conf.py
- [ ] setup.py
- [ ] src/requests/__init__.py
- [ ] src/requests/__version__.py
- [ ] src/requests/_internal_utils.py
- [ ] src/requests/_types.py
- [ ] src/requests/adapters.py
- [ ] src/requests/api.py
- [ ] src/requests/auth.py
- [ ] src/requests/certs.py
- [ ] src/requests/compat.py
- [ ] src/requests/cookies.py
- [ ] src/requests/exceptions.py
- [ ] src/requests/help.py
- [ ] src/requests/hooks.py
- [ ] src/requests/models.py
- [ ] src/requests/packages.py
- [ ] src/requests/sessions.py
- [ ] src/requests/status_codes.py
- [ ] src/requests/structures.py
- [ ] src/requests/utils.py

**NONE:** [x]

**EXTRA:**

**NOTES:** Contribution process, code review, code style, 'docs live in docs/'. No assertion about library behavior/signature/defaults/errors. NONE (a contributing note is a real answer).
---

## Case 11 — `psf/requests` · `docs/user/authentication.rst`

- **read** `review/2c/text/psf-requests/doc/docs-user-authentication.rst` (5854 chars)
- **code** `review/2c/text/psf-requests/code`
- **tree** `dae7ef63b4df`

- [ ] docs/_themes/flask_theme_support.py
- [ ] docs/conf.py
- [ ] setup.py
- [ ] src/requests/__init__.py
- [ ] src/requests/__version__.py
- [ ] src/requests/_internal_utils.py
- [ ] src/requests/_types.py
- [ ] src/requests/adapters.py
- [x] src/requests/api.py
- [x] src/requests/auth.py
- [ ] src/requests/certs.py
- [ ] src/requests/compat.py
- [ ] src/requests/cookies.py
- [ ] src/requests/exceptions.py
- [ ] src/requests/help.py
- [ ] src/requests/hooks.py
- [ ] src/requests/models.py
- [ ] src/requests/packages.py
- [x] src/requests/sessions.py
- [ ] src/requests/status_codes.py
- [ ] src/requests/structures.py
- [x] src/requests/utils.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** HTTPBasicAuth/HTTPDigestAuth (auth.py); tuple shorthand -> Basic (auth.py, wired in models.py — models.py also defensible); netrc lookup + trust_env + NETRC env + search paths (sessions.py calls get_netrc_auth in utils.py); Session() (sessions.py); requests.get(auth=) (api.py). requests-oauthlib is external.
---

## Case 12 — `psf/requests` · `docs/user/install.rst`

- **read** `review/2c/text/psf-requests/doc/docs-user-install.rst` (1038 chars)
- **code** `review/2c/text/psf-requests/code`
- **tree** `dae7ef63b4df`

- [ ] docs/_themes/flask_theme_support.py
- [ ] docs/conf.py
- [ ] setup.py
- [ ] src/requests/__init__.py
- [ ] src/requests/__version__.py
- [ ] src/requests/_internal_utils.py
- [ ] src/requests/_types.py
- [ ] src/requests/adapters.py
- [ ] src/requests/api.py
- [ ] src/requests/auth.py
- [ ] src/requests/certs.py
- [ ] src/requests/compat.py
- [ ] src/requests/cookies.py
- [ ] src/requests/exceptions.py
- [ ] src/requests/help.py
- [ ] src/requests/hooks.py
- [ ] src/requests/models.py
- [ ] src/requests/packages.py
- [ ] src/requests/sessions.py
- [ ] src/requests/status_codes.py
- [ ] src/requests/structures.py
- [ ] src/requests/utils.py

**NONE:** [x]

**EXTRA:**

**NOTES:** Install guide: pip install, git clone, embed in package. No claim about code behavior. NONE (an install guide is a real answer).
---

## Case 13 — `pallets/flask` · `docs/config.rst`

- **read** `review/2c/text/pallets-flask/doc/docs-config.rst` (28994 chars)
- **code** `review/2c/text/pallets-flask/code`
- **tree** `d73fa1cdcbd8`

- [ ] docs/conf.py
- [ ] examples/celery/make_celery.py
- [ ] examples/celery/src/task_app/__init__.py
- [ ] examples/celery/src/task_app/tasks.py
- [ ] examples/celery/src/task_app/views.py
- [ ] examples/javascript/js_example/__init__.py
- [ ] examples/javascript/js_example/views.py
- [ ] examples/tutorial/flaskr/__init__.py
- [ ] examples/tutorial/flaskr/auth.py
- [ ] examples/tutorial/flaskr/blog.py
- [ ] examples/tutorial/flaskr/db.py
- [ ] src/flask/__init__.py
- [ ] src/flask/__main__.py
- [x] src/flask/app.py
- [ ] src/flask/blueprints.py
- [ ] src/flask/cli.py
- [x] src/flask/config.py
- [ ] src/flask/ctx.py
- [ ] src/flask/debughelpers.py
- [ ] src/flask/globals.py
- [ ] src/flask/helpers.py
- [ ] src/flask/json/__init__.py
- [ ] src/flask/json/provider.py
- [ ] src/flask/json/tag.py
- [ ] src/flask/logging.py
- [x] src/flask/sansio/app.py
- [ ] src/flask/sansio/blueprints.py
- [ ] src/flask/sansio/scaffold.py
- [x] src/flask/sessions.py
- [ ] src/flask/signals.py
- [ ] src/flask/templating.py
- [ ] src/flask/testing.py
- [ ] src/flask/typing.py
- [ ] src/flask/views.py
- [ ] src/flask/wrappers.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** Flask.config is a dict subclass + Config class and default_config live in config.py; the builtin config-value defaults (DEBUG/TESTING/PROPAGATE_EXCEPTIONS/SECRET_KEY/...) and the debug/config attrs are defined in sansio/app.py (concrete Flask in app.py); session-cookie config values (SESSION_COOKIE_*, SECRET_KEY, SECRET_KEY_FALLBACKS) are consumed in sessions.py.
---

## Case 14 — `pallets/flask` · `docs/errorhandling.rst`

- **read** `review/2c/text/pallets-flask/doc/docs-errorhandling.rst` (18374 chars)
- **code** `review/2c/text/pallets-flask/code`
- **tree** `d73fa1cdcbd8`

- [ ] docs/conf.py
- [ ] examples/celery/make_celery.py
- [ ] examples/celery/src/task_app/__init__.py
- [ ] examples/celery/src/task_app/tasks.py
- [ ] examples/celery/src/task_app/views.py
- [ ] examples/javascript/js_example/__init__.py
- [ ] examples/javascript/js_example/views.py
- [ ] examples/tutorial/flaskr/__init__.py
- [ ] examples/tutorial/flaskr/auth.py
- [ ] examples/tutorial/flaskr/blog.py
- [ ] examples/tutorial/flaskr/db.py
- [ ] src/flask/__init__.py
- [ ] src/flask/__main__.py
- [x] src/flask/app.py
- [ ] src/flask/blueprints.py
- [ ] src/flask/cli.py
- [ ] src/flask/config.py
- [ ] src/flask/ctx.py
- [ ] src/flask/debughelpers.py
- [ ] src/flask/globals.py
- [ ] src/flask/helpers.py
- [ ] src/flask/json/__init__.py
- [ ] src/flask/json/provider.py
- [ ] src/flask/json/tag.py
- [x] src/flask/logging.py
- [x] src/flask/sansio/app.py
- [ ] src/flask/sansio/blueprints.py
- [x] src/flask/sansio/scaffold.py
- [ ] src/flask/sessions.py
- [ ] src/flask/signals.py
- [ ] src/flask/templating.py
- [ ] src/flask/testing.py
- [ ] src/flask/typing.py
- [ ] src/flask/views.py
- [ ] src/flask/wrappers.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** errorhandler/register_error_handler in sansio/scaffold.py; default 500 page, log-to-Flask.logger, handle_exception/handle_user_exception/handle_http_exception in app.py; the logger property in logging.py + sansio/app.py; TESTING/PROPAGATE_EXCEPTIONS/TRAP_* behavior on the config in sansio/app.py. Werkzeug HTTPException classes are external.
---

## Case 15 — `pallets/flask` · `docs/patterns/mongoengine.rst`

- **read** `review/2c/text/pallets-flask/doc/docs-patterns-mongoengine.rst` (2882 chars)
- **code** `review/2c/text/pallets-flask/code`
- **tree** `d73fa1cdcbd8`

- [ ] docs/conf.py
- [ ] examples/celery/make_celery.py
- [ ] examples/celery/src/task_app/__init__.py
- [ ] examples/celery/src/task_app/tasks.py
- [ ] examples/celery/src/task_app/views.py
- [ ] examples/javascript/js_example/__init__.py
- [ ] examples/javascript/js_example/views.py
- [ ] examples/tutorial/flaskr/__init__.py
- [ ] examples/tutorial/flaskr/auth.py
- [ ] examples/tutorial/flaskr/blog.py
- [ ] examples/tutorial/flaskr/db.py
- [ ] src/flask/__init__.py
- [ ] src/flask/__main__.py
- [ ] src/flask/app.py
- [ ] src/flask/blueprints.py
- [ ] src/flask/cli.py
- [ ] src/flask/config.py
- [ ] src/flask/ctx.py
- [ ] src/flask/debughelpers.py
- [ ] src/flask/globals.py
- [ ] src/flask/helpers.py
- [ ] src/flask/json/__init__.py
- [ ] src/flask/json/provider.py
- [ ] src/flask/json/tag.py
- [ ] src/flask/logging.py
- [ ] src/flask/sansio/app.py
- [ ] src/flask/sansio/blueprints.py
- [ ] src/flask/sansio/scaffold.py
- [ ] src/flask/sessions.py
- [ ] src/flask/signals.py
- [ ] src/flask/templating.py
- [ ] src/flask/testing.py
- [ ] src/flask/typing.py
- [ ] src/flask/views.py
- [ ] src/flask/wrappers.py

**NONE:** [x]

**EXTRA:**

**NOTES:** All claims are about flask_mongoengine/mongoengine (external libraries) and MONGODB_SETTINGS. It instantiates Flask and reads app.config, but asserts nothing checkable about Flask's own behavior/signatures. NONE (parallel to requests recommended.rst).
---

## Case 16 — `pallets/flask` · `docs/patterns/requestchecksum.rst`

- **read** `review/2c/text/pallets-flask/doc/docs-patterns-requestchecksum.rst` (1861 chars)
- **code** `review/2c/text/pallets-flask/code`
- **tree** `d73fa1cdcbd8`

- [ ] docs/conf.py
- [ ] examples/celery/make_celery.py
- [ ] examples/celery/src/task_app/__init__.py
- [ ] examples/celery/src/task_app/tasks.py
- [ ] examples/celery/src/task_app/views.py
- [ ] examples/javascript/js_example/__init__.py
- [ ] examples/javascript/js_example/views.py
- [ ] examples/tutorial/flaskr/__init__.py
- [ ] examples/tutorial/flaskr/auth.py
- [ ] examples/tutorial/flaskr/blog.py
- [ ] examples/tutorial/flaskr/db.py
- [ ] src/flask/__init__.py
- [ ] src/flask/__main__.py
- [ ] src/flask/app.py
- [ ] src/flask/blueprints.py
- [ ] src/flask/cli.py
- [ ] src/flask/config.py
- [ ] src/flask/ctx.py
- [ ] src/flask/debughelpers.py
- [x] src/flask/globals.py
- [ ] src/flask/helpers.py
- [ ] src/flask/json/__init__.py
- [ ] src/flask/json/provider.py
- [ ] src/flask/json/tag.py
- [ ] src/flask/logging.py
- [ ] src/flask/sansio/app.py
- [ ] src/flask/sansio/blueprints.py
- [x] src/flask/sansio/scaffold.py
- [ ] src/flask/sessions.py
- [ ] src/flask/signals.py
- [ ] src/flask/templating.py
- [ ] src/flask/testing.py
- [ ] src/flask/typing.py
- [ ] src/flask/views.py
- [ ] src/flask/wrappers.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** Uses the `request` proxy (globals.py) and @app.route (route decorator in sansio/scaffold.py). request.environ/.form/.files are Werkzeug Request attributes (not in the flask code pool) — noted, not marked. The ChecksumCalcStream/generate_checksum code is user code, not flask.
---

## Case 17 — `pallets/flask` · `docs/patterns/streaming.rst`

- **read** `review/2c/text/pallets-flask/doc/docs-patterns-streaming.rst` (3307 chars)
- **code** `review/2c/text/pallets-flask/code`
- **tree** `d73fa1cdcbd8`

- [ ] docs/conf.py
- [ ] examples/celery/make_celery.py
- [ ] examples/celery/src/task_app/__init__.py
- [ ] examples/celery/src/task_app/tasks.py
- [ ] examples/celery/src/task_app/views.py
- [ ] examples/javascript/js_example/__init__.py
- [ ] examples/javascript/js_example/views.py
- [ ] examples/tutorial/flaskr/__init__.py
- [ ] examples/tutorial/flaskr/auth.py
- [ ] examples/tutorial/flaskr/blog.py
- [ ] examples/tutorial/flaskr/db.py
- [ ] src/flask/__init__.py
- [ ] src/flask/__main__.py
- [ ] src/flask/app.py
- [ ] src/flask/blueprints.py
- [ ] src/flask/cli.py
- [ ] src/flask/config.py
- [ ] src/flask/ctx.py
- [ ] src/flask/debughelpers.py
- [x] src/flask/globals.py
- [x] src/flask/helpers.py
- [ ] src/flask/json/__init__.py
- [ ] src/flask/json/provider.py
- [ ] src/flask/json/tag.py
- [ ] src/flask/logging.py
- [ ] src/flask/sansio/app.py
- [ ] src/flask/sansio/blueprints.py
- [x] src/flask/sansio/scaffold.py
- [x] src/flask/sessions.py
- [ ] src/flask/signals.py
- [x] src/flask/templating.py
- [ ] src/flask/testing.py
- [ ] src/flask/typing.py
- [ ] src/flask/views.py
- [ ] src/flask/wrappers.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** stream_template/stream_template_string in templating.py; stream_with_context + the 'request proxy inactive -> RuntimeError in generator' behavior in helpers.py (request proxy in globals.py); @app.route/@app.get in sansio/scaffold.py; session access + Vary: cookie / Set-Cookie behavior in sessions.py.
---

## Case 18 — `pallets/flask` · `docs/templating.rst`

- **read** `review/2c/text/pallets-flask/doc/docs-templating.rst` (8933 chars)
- **code** `review/2c/text/pallets-flask/code`
- **tree** `d73fa1cdcbd8`

- [ ] docs/conf.py
- [ ] examples/celery/make_celery.py
- [ ] examples/celery/src/task_app/__init__.py
- [ ] examples/celery/src/task_app/tasks.py
- [ ] examples/celery/src/task_app/views.py
- [ ] examples/javascript/js_example/__init__.py
- [ ] examples/javascript/js_example/views.py
- [ ] examples/tutorial/flaskr/__init__.py
- [ ] examples/tutorial/flaskr/auth.py
- [ ] examples/tutorial/flaskr/blog.py
- [ ] examples/tutorial/flaskr/db.py
- [ ] src/flask/__init__.py
- [ ] src/flask/__main__.py
- [x] src/flask/app.py
- [ ] src/flask/blueprints.py
- [ ] src/flask/cli.py
- [ ] src/flask/config.py
- [ ] src/flask/ctx.py
- [ ] src/flask/debughelpers.py
- [x] src/flask/globals.py
- [x] src/flask/helpers.py
- [ ] src/flask/json/__init__.py
- [ ] src/flask/json/provider.py
- [ ] src/flask/json/tag.py
- [ ] src/flask/logging.py
- [x] src/flask/sansio/app.py
- [x] src/flask/sansio/blueprints.py
- [x] src/flask/sansio/scaffold.py
- [ ] src/flask/sessions.py
- [ ] src/flask/signals.py
- [x] src/flask/templating.py
- [ ] src/flask/testing.py
- [ ] src/flask/typing.py
- [ ] src/flask/views.py
- [ ] src/flask/wrappers.py

**NONE:** [ ]

**EXTRA:**

**NOTES:** autoescape rules + render_template/render_template_string in templating.py; select_jinja_autoescape/jinja_env/create_jinja_environment in sansio/app.py (+app.py); standard context config/request/session/g in globals.py and url_for/get_flashed_messages in helpers.py; template_filter/add_template_filter/template_test/template_global in sansio/app.py, context_processor in sansio/scaffold.py; update_template_context in templating.py/app.py; Blueprint app_* variants in sansio/blueprints.py.
---
