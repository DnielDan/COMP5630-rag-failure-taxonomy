# One real example per failure type

Drawn from **Dense RAG (standard)** (falls back to other systems). Human-labelled rows preferred.

## R1 · Retrieval miss  (27 total)

- **System:** Dense RAG (standard)  ·  **Type:** Lookup  ·  `look-004`
- **Question:** What is the primary purpose of the Requests library in comparison to FastAPI?
- **Gold answer:** Requests is a library to interact with APIs as a client, while FastAPI is a library to build APIs as a server.
- **System answer:** I don't know based on the provided documentation.
- **Gold chunk retrieved:** 0/1
- **Retrieved sections:** Using the Request Directly; Benchmarks > Benchmarks > Benchmarks and speed; FastAPI; Request Forms and Files; Advanced Dependencies > Advanced Dependencies > Parameterized dependencies
- **Why (human label):** The retrieved passages contain information about FastAPI's purpose, but the system did not use this information to answer the question.

## R2 · Retrieved, ignored  (3 total)

- **System:** Dense RAG (standard)  ·  **Type:** Multi-hop  ·  `mult-023`
- **Question:** How can you use OpenAPI callbacks in FastAPI to handle asynchronous responses with additional status codes and models?
- **Gold answer:** You can use OpenAPI callbacks in FastAPI to document external APIs that will be called back with information from the original request. Additionally, you can declare extra responses with different status codes and models using the 'responses' parameter in path operation decorators. This allows you to handle asynchronous responses with specific status codes and include models for those responses in the OpenAPI schema.
- **System answer:** I don't know based on the provided documentation.
- **Gold chunk retrieved:** 1/2
- **Retrieved sections:** Additional Status Codes; Additional Responses in OpenAPI; Additional Responses in OpenAPI; OpenAPI Callbacks; Custom Response - HTML, Stream, File, others
- **Why (human label):** The needed information about OpenAPI callbacks and additional responses is present in the retrieved passages, but the system answer did not utilize it.

## R3 · Right chunk, wrong answer  (46 total)

- **System:** Dense RAG (standard)  ·  **Type:** Ambiguous  ·  `ambi-004`
- **Question:** How does OAuth2 handle permissions?
- **Gold answer:** AMBIGUOUS. Reading 1 (The question refers to the specific way OAuth2 uses scopes as strings to declare permissions.): OAuth2 handles permissions using scopes, which are strings that declare specific permissions required, like 'users:read'. Reading 2 (The question refers to the broader context of OAuth2's role in authentication and authorization.): OAuth2 handles permissions as part of its specification for authentication and authorization, often used in 'login with' systems.
- **System answer:** OAuth2 handles permissions through the use of "scopes," which are strings that declare specific permissions required for accessing certain resources. Each scope represents a particular permission, such as `users:read` or `users:write` [1][2]. When a user authenticates, they can specify which scopes they want to authorize, and these scopes are checked independently for each path operation in the API [5]. This allows for a fine-grained permission system, enabling applications to request only the permissions they need [1][3].
- **Gold chunk retrieved:** 2/2
- **Retrieved sections:** OAuth2 scopes; OAuth2 scopes; OAuth2 with Password (and hashing), Bearer with JWT tokens > OAuth2 with Password (and hashing), Bearer with JWT tokens > Update the `/token` *path operation*; Security; OAuth2 scopes > OAuth2 scopes > Verify the `scopes`
- **Why (human label):** The system answer correctly uses the retrieved passages to explain scopes but fails to address the broader context of OAuth2's role in authentication and authorization, which is also present in the retrieved passages.

## R4 · Hallucinated citation  (0 total)

_No examples._

## R5 · No-answer overreach  (0 total)

_No examples._

## R6 · Multi-hop failure  (26 total)

- **System:** Dense RAG (standard)  ·  **Type:** Multi-hop  ·  `mult-025`
- **Question:** How does FastAPI ensure compatibility with Pydantic while also using Python type declarations for data validation and conversion?
- **Gold answer:** FastAPI ensures compatibility with Pydantic by including its tests with Pydantic's own tests, making sure that new versions of Pydantic above 1.0.0 are always compatible with FastAPI. At the same time, FastAPI uses standard Python type declarations to define requirements, convert, and validate data, which simplifies the process by avoiding additional classes or decorators.
- **System answer:** FastAPI is built on top of Pydantic, which allows it to use Python type declarations for data validation and conversion. FastAPI utilizes these type declarations to define requirements for various request components, convert incoming data to the required types, validate the data, and document the API using OpenAPI. This integration enables automatic error generation for invalid data and simplifies the development process by handling much of the work behind the scenes [2][3]. 

Additionally, FastAPI supports both Pydantic models and standard dataclasses, leveraging Pydantic's capabilities for data validation and serialization [2].
- **Gold chunk retrieved:** 1/2
- **Retrieved sections:** Migrate from Pydantic v1 to Pydantic v2; Using Dataclasses; Python Types Intro; Response Model - Return Type; Migrate from Pydantic v1 to Pydantic v2
- **Why (human label):** The retrieved passages contain the necessary information about FastAPI's compatibility with Pydantic through testing, but the system answer did not utilize this information.
