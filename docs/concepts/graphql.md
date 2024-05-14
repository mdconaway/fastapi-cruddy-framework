## GraphQL

Cruddy now supports GraphQL Read Operations! The GraphQL class APIs are considered unstable at the moment, but the GraphQL feature set is still <i>secure</i>, so it is safe to add it on top of your APIs!

For examples on how to integrate GraphQL functionality with your cruddy-based app, inspect the [example server](examples/fastapi_cruddy_sqlite).

Additional documentation will be added once the GraphQL API stabilizes! The cruddy exports that are directly needed to enable GraphQL are:

```
GraphQLController
GraphQLRequestCache
GraphQLResolverService
create_module_resolver
graphql_where_synthesizer
generate_gql_loader_and_type
GQL_WHERE_REPLACEMENT_CHARACTER
CruddyGQLDateTime
CruddyGQLObject
CruddyGQLArray
CruddyCreatedUpdatedGQLOverrides
CruddyGQLOverrides
```
