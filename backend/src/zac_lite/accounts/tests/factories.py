import factory


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "sekrit")

    class Meta:
        model = "accounts.User"

    class Params:
        with_token = factory.Trait(
            auth_token=factory.RelatedFactory(
                "zac_lite.accounts.tests.factories.TokenFactory",
                factory_related_name="user",
            )
        )


class TokenFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = "authtoken.Token"
