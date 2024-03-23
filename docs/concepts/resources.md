### Resource

The `Resource` class is the fundamental building block of fastapi-cruddy-framework. Your resource instances define the union of your models, resource "controller" (which is a fastapi router with baked-in CRUD logic), business policies, repository abstraction layer, any resource lifecycle hook, and database adapter. Fortunately for you, the user, everything is essentially ready-to-go out of the box. Like [sails-ember-rest](https://github.com/mdconaway/sails-ember-rest) or [Ruby on Rails](https://rubyonrails.org/), you can now focus all of your development time on creating reusable policies (which contain your business logic that lies just above your CRUD endpoints), defining your models, and extending your resource controllers to add one-off actions like "login" or "change password".

Lifecycle actions allow you to alter query configurations or record data before or after it is persisted to a database, or perform some other task before replying to the user. All of your resources should be loaded by the [router factory](/api/router_generator) to ensure that relationships and routes are resolved in the correct order. Don't forget, <b>only plug the master router into your application in the fastapi `startup` hook!</b>

<b>Resource Nuances:</b>

- Defining your policies is done at definition time!
- Lifecycle actions occur immediately before and after any database interaction your CRUD controllers make
- Lifecycle actions passed into the Resource constructor to interact with your queries or data <b>MUST</b> be `async` functions.
- Policies are run in the exact order in which they are included in the `list` sent to the resource definition.
- `policies_universal` apply to ALL CRUD routes, and always run <i>BEFORE</i> action specific policy chains.
- Action specific policies run <i>AFTER</i> all `policies_universal` have resolved successfully.
- Each endpoint is protected by `policies_universal` + `policies_<action>`.
- One-to-Many and Many-to-Many sub-routes (like /users/{id}/posts) will be protected by the policy chain: `user.policies_universal` + `user.policies_get_one` + `posts.policies_get_many`. Security, security, security!
- Blocking user REST modification of certain relationships via the default CRUD controller is also done at definition time!
- `protected_relationships` is a `list[str]` with each string indicating a one-to-many or many-to-many relationship that should not be allowed to update via the default CRUD actions.
- You should define your application-wide adapter elsewhere and pass it into the resource instance.
- Resources cannot span different databases.

<b>Available Policy Chain Definitions:</b>

- `policies_universal`
- `policies_create`
- `policies_update`
- `policies_delete`
- `policies_get_one`
- `policies_get_many`

<b>Available ASYNC Lifecycle Hooks:</b>

- `lifecycle_before_create`
- `lifecycle_after_create`
- `lifecycle_before_update`
- `lifecycle_after_update`
- `lifecycle_before_delete`
- `lifecycle_after_delete`
- `lifecycle_before_get_one`
- `lifecycle_after_get_one`
- `lifecycle_before_get_all`
- `lifecycle_after_get_all`
- `lifecycle_before_set_relations`
- `lifecycle_after_set_relations`

<b>Available Relationship Blocks:</b>

- `protected_relationships`

<b>Updating Relationships:</b>

- You can update relationships via either CREATE or UPDATE actions against each base resource!

As you will discover, your resource's create and update models will automatically gain "shadow" properties where one-to-many and many-to-many relationships exist. These properties expect a client to send a list of IDs that specify the foreign records that relate to the target record. So - if a user is a member of many groups, and a group can have many users, you could update the users in a group by sending a property `"users": [1,2,3,4,5]` within the `group` payload object you send to the `POST /groups` or `PATCH /groups` routes/actions. It will all be clear when you look at the SWAGGER docs generated for your API.
