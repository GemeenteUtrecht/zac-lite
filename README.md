# ZAC lite

The "ZAC lite" is a stripped down "version" of the zaakafhandelcomponent. It is intended
for small modifications to zaken made by people that are not necessarily a staff member
(read: external people). It integrates primarily with Camunda.

## Camunda (user tasks) as orchestrator

The ultimate end goal is to code the ZAC lite once in a very dynamic fashion, so that
it integrates with other services and it's UI is driven by configuration. Configuration
manifests itself in the form of Camunda user task definitions with the attached form
definitions.

A user task is always a task that requires user input. What input exactly is required,
can be specified in the task form (which is a Camunda extension) or via a form key.

Directly specified forms are flat and very simple, but they define which subsequent
input is available in the process for steps after the user task is completed.

Form keys can be used to refer to internal, hard-coded forms, or in more ideal scenario,
to forms defined in a e-forms solution (such as Open Form).

### Challenges

One challenge is of course being able to provide sufficient context from the particular
process instance (e.g.: which zaak should we retrieve existing documents from) and
communicate that from ZAC lite BFF to ZAC lite UI. There's also the matter of when
the input is collected and subsequently submitted to the form, to process that form
and have the resulting variables injected in the proces when the user task itself
is completed.

### Approach

At first, we'll program the forms as they're required for this particular proces, and
in later phases we look at how to make this more generic. There are hopes that Open
Forms will then no longer be in a prototype phase, and we'll be able to use the
appropriate API's to bring everything together.

## Architecture

We're starting a new project and repository for ZAC lite, rather than building an
extension in the existing ZAC. This provides us with an app that can be deployed
separately on its own domain, and there's less risk of accidentally leaking data that
should not be accessible to externals.

The backend will be implemented in Django + django-rest-framework, providing a private
API to be consumed by the frontend.

The frontend will be implemented in Angular, re-using UI components that have been
developed or are being developed for the ZAC as much as possible. The frontend will
only consume the private BFF API.

The backend will be configured to:

- fetch data from Open Zaak
- fetch data from Documenten API
- write data to Open Zaak and Documenten API
- interact with the Camunda REST API

We'll be using the libraries `zgw-consumers`, `django-camunda` to achieve that.
Additionally the internal API will be documented with `drc-spectacular`.

## Security considerations

As the ZAC lite is aimed at external people, we cannot use ADFS log-in, since the people
providing the required input do not have a Utrecht login.

For this purpose, we will generate limited-time and limited-use URLs that are
cryptographically secure. The URLs contain a reference to the ID of the user task so that
it can be retrieved from the Camunda API. The URL also contains a token, which is some
form of cryptographic signature. The input for the token is:

- number of days valid
- camunda task ID
- some data that changes when the task has been executed

This ensures that replay attacks are not possible, and that you cannot randomly execute
user tasks by guessing IDs.

This results in URLs that automatically expire after the number of configured days, and
are no longer usable as soon as the user task has been performed. The URL will be
e-mailed to the relevant external entity.

In the future, it's possible to use a user task assignee expression in the form of
`bsn:123456782` for example, which can be combined with a DigiD login to ensure that
only the correct person can execute the task.


## Technical tickets

Below is a summary of the backend work required to achieve this.

### Create application repository

Create github repository + implement basic layout:

```
backend
    <default-project> django layout
frontend
    <to be set up by Kelvin>
docker stuff
    <see ZAC>
```

### Set up required libraries

* `zgw-consumers`
* `drf`
* `drf-spectacular`
* `django-auth-adfs-db` (for administrators)
* `django-camunda`
* `django-privates`

### Set up endpoint to generate magic links

Reference: `django.contrib.auth.tokens` and the various forms/views related to password
resets in `django.contrib.auth`.

The magic, secure link must be generated by the ZAC lite itself, since it usually uses
the `settings.SECRET_KEY` which must stay private to ZAC lite.

Request:

```http
POST http://localhost:8000/api/v1/user-link HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "taskId": "753e682d-b9af-4efa-811f-a2c8b0b51967"
}
```

Response:

```json
{
    "url": "http://localhost:8000/ui/perform-task/<tidb64>/<token>"
}
```

Where `tidb64` is the urlsafe base64 encoded task ID, and the token the
cryptographically secure token.

The token should use as hash input:

* `Task.assignee`
* `Task.due`
* `Task.delegationState`
* `Task.owner`
* `Task.suspended`
* `Task.formKey`

If any of those task properties change after the token/URL is generated, the token will
be invalidated.

This endpoint will be called by BPTL work units in the Camunda process, so it should
have `TokenAuthentication` auth backend.

### Set up endpoint to retrieve user task data

When the frontend URL `http://localhost:8000/ui/perform-task/<tidb64>/<token>` gets hit,
the frontend shall make an API call to retrieve the relevant data to display the
form. At first instance, this form will be hardcoded to a `formKey` of
`zac-lite:zaak-documents`.

The following API call must be implemented:

```http
GET http://localhost:8000/api/v1/task-data/<tidb64>/<token> HTTP/1.1
```

The response should look like (HTTP 200):

```json
{
    "form": "zac-lite:zaak-documents",
    "task": {
        "id": "753e682d-b9af-4efa-811f-a2c8b0b51967",
        "name": "Document(en) wijzigen",
        "assignee": "",
        "created": "YYYY-MM-DDTHH:mm:ss.SSZ"
    },
    "context": {
        "zaak": {
            "identificatie": "ZAAK-2021-0000000001",
            "zaaktype": {
                "omschrijving": "Vastleggen rapportage NEN 2580"
            }
        },
        "documents": [
            {
                "url": "https://drc.utrechtproeftuin.nl/api/v1/enkelvoudiginformatieobjecten/79dc383d",
                "title": "Eerste verdieping",
                "size": 4096,
                "documentType": "https://openzaak.utrechtproeftuin.nl/catalogi/api/v1/informatieobjecttypen/1a1d4fb2"
            },
            {
                "url": "https://drc.utrechtproeftuin.nl/api/v1/enkelvoudiginformatieobjecten/079cf380",
                "title": "Tweede verdieping",
                "size": 2048,
                "documentType": "https://openzaak.utrechtproeftuin.nl/catalogi/api/v1/informatieobjecttypen/1a1d4fb2"
            }
        ],
        "documentTypes": [
            {
                "url": "https://openzaak.utrechtproeftuin.nl/catalogi/api/v1/informatieobjecttypen/1a1d4fb2",
                "omschrijving": "Plattegrond"
            },
            {
                "url": "https://openzaak.utrechtproeftuin.nl/catalogi/api/v1/informatieobjecttypen/63eb5ef4",
                "omschrijving": "bijlage"
            }
        ],
        "toelichtingen": "${task.processInstance.variables['toelichtingen']}"
    }
}
```

Note that the whole `context` key will have a different schema depending on the `form`
key value, so in the API documentation it should be a simple object without pre-defined
schema. At first, this is the context that the frontend will support until we figure out
a generic solution.

(using the [`jq`](https://stedolan.github.io/jq/manual/) syntax could be viable here!
[TODO: there's also another python lib that makes transforming documents quite easy,
must recollect what the name was])

When the data is retrieved for the task, the backend must validate the token first and
foremost:

1. Use `tidb64` and decode it to obtain the task ID
2. Fetch the task from Camunda
    * if Camunda 404's, the task has been executed or deleted -> response back with a 404
      and error messages indicating the task could not be found
3. Using the task information, validate the provided token. If the token is not valid,
   return a HTTP 403
    * it could be that the token is invalid because it was spoofed
    * it could be that the token has expired
    * it could be that the task itself has changed, invalidating the token in the
      process
4. If the token is valid, retrieve the process variables and look up the zaak from the
   process to build the context.

#### Set up endpoint to upload documents

Because the entire user-facing form should be processed as a whole, and there is a
possibility many documents must be changed or added at once, we split this up and
create a dedicated endpoint for temporary uploads.

```http
POST http://localhost:8000/api/v1/files HTTP/1.1
Host: localhost:8000
Accept: application/json
Content-Type: multipart/form-data; boundary=9051914041544843365972754266

--9051914041544843365972754266
Content-Disposition: form-data; name="tidb64"

<tidb64>
--9051914041544843365972754266
Content-Disposition: form-data; name="token"

<token>
--9051914041544843365972754266
Content-Disposition: form-data; name="file"; filename="Derde verdieping.ext"
Content-Type: application/octet-stream

<binary content>
--9051914041544843365972754266--

```

Response:

```json
{
    "id": "d6f90bf4-699b-4741-a759-19c4cf84344d"
}
```

This file should be stored in the database (metadata) and the actual file contents on
disk (using `django-privates`). Metadata should at least contain the file name, which
will be propagated to the documents API later.

It's up to the frontend to correlate the UUID with the subsequent API call(s).

Note that in nginx the `client_max_bodysize` must be set appropriately, and in Django
the setting `DATA_UPLOAD_MAX_MEMORY_SIZE` (default is 2.5MB).

The `tidb64` and `token` keys must be part of the body, and the endpoint must validate
these. This protects against anonymous users flooding the zac-test with file uploads
that will never be cleared (DDOS vector).

#### Set up endpoint to submit user task

This endpoint is called by the frontend when the user submits the user task (form).

It must:

* make all the necessary changes, specific to the form key
* derive the (new) process variables
* complete the user task with the derived process variables

In particular, since we're at first instance hard-coding this, we can build an endpoint
specifically for the `zac-lite:zaak-documents` form key:

```http
POST http://localhost:8000/api/v1/tasks/zac-lite:zaak-documents HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
    "tidb64": "<tidb64>",
    "token": "<token>",
    "newDocuments": [
        {
            "id": "d6f90bf4-699b-4741-a759-19c4cf84344d",
            "documentType": "https://openzaak.utrechtproeftuin.nl/catalogi/api/v1/informatieobjecttypen/63eb5ef4"
        }
    ],
    "replacedDocuments": [
        {
            "id": "1b326772-3519-4435-9d88-0618060f9ab6",
            "old": "https://drc.utrechtproeftuin.nl/api/v1/enkelvoudiginformatieobjecten/79dc383d"
        }
    ]
}
```

The `newDocuments` is reserved for new files to be added to the zaak. `id` refers to
a file upload ID, while the `documentType` show what the `informatieobjecttype` of the
new document should be.

Validation must check that:

- `id` is an existing document belonging to this task ID
- `documentType` is contained by the `task-data` endpoint in the `context.documentTypes`

`replacedDocuments` is reserved for existing documents that needed to be modified. The
`old` key refers to the current, existing document related to the zaak. `id` must
refer to a file upload.

Validation must check that:

- `id` is an existing document belonging to this task ID
- `old` is contained by the `context.documents` from the `task-data` endpoint.

Of course, here again validation must check that `tidb64` and `token` still validate to
protect against abuse.

If everything validates, only then mutations make take place:

* create the new documents (and store the URLs)
* update the existing documents with the new content
  `EnkelvoudigInformatieobject.inhoud` AND meta-information such as filename/titel which
  should be stored with the file upload.
* complete the user task in the Camunda API

Completing the user task should set process variables:

* `updatedDocuments`: `["<url of updated doc>"]`
* `newDocuments`: `["<url of new doc>"]` so that the rest of the process can relate
  document and zaak.
