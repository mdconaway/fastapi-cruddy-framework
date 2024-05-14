### ControllerConfigurator

The `ControllerConfigurator` is a configuration function invoked by the `Resource` class after SQL Alchemy has resolved all model relationships. You shouldn't need to interact with this function, but if you're a super advanced user, or wunderkind, maybe you will find a reason to need this. In essence, this function builds out all of the basic CRUD logic for a resource, after the resource has constructed a repository and generated the shadow schemas for your models. This is where your CRUD routes and sub-routes are auto-magically configured.

The controller/router configured by each of your `Resource` objects will allow the base resource or its relationships to be queried from the client via an arbitrarily complex `where` object (JSON encoded query parameter).

Invalid attributes or ops are just dropped. (May change in the future)

Improvements that will be made in the near future:

1. Conditional table joins for relationships to...
2. Make resources searchable with joined relationships via dot notation in the `where` object!
3. Maybe throw an error if a bad search field is sent? (Will help UI devs)

Clients can build an arbitrarily deep query with a JSON dictionary, sent via a query parameter in a JSON object that generally contains all possible filter operators along with "and," "or," and "not" conditions.

Field level and boolean operators begin with a * character. This will nearly always translate down to the sqlalchemy level, where it is up to the model class to determine what operations are possible on each model attribute. The top level query of a `where` object is an implicit AND. To do an OR, the base key of the search must be `*or`, as in the below examples:

`/resource?where={"*or":{"first_name":"bilbo","last_name":"baggins"}}`

`/resource/{id}/relationship?where={"*or":{"first_name":{"*contains":"bilbo"},"last_name":"baggins"}}`

`/resource?where={"*or":{"first_name":{"*endswith":"bilbo"},"last_name":"baggins","*and":{"email":{"*contains":"@"},"first_name":{"*contains":"helga"}}}}`

`/resource?where={"*or":{"first_name":{"*endswith":"bilbo"},"last_name":"baggins","*and":[{"email":{"*contains":"@"}},{"email":{"*contains":"helga"}}]}}`

The following query would be an implicit \*and:

`/resource?where=[{"first_name":{"*endswith":"bilbo"}},{"last_name":"baggins"}]`

As would the following query:

`/resource/{id}/relationship?where={"first_name":{"*endswith":"bilbo"},"last_name":"baggins"}`

"Dot" notation is currently supported for JSON or JSON-like columns. The following queries showcase this:

`/resource?where={"user.config.favoriteColor":{"*eq":"black"}}`

`/resource?where={"favorites.":{"*contained_by":{"tags":["foo","bar","baz]}}}`

`/resource?where={"favorites.tags":{"*contains":["foo"]}}`

<p align="right">(<a href="#readme-top">back to top</a>)</p>
