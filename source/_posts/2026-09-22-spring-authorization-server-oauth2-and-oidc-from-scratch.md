---
title: "Spring Authorization Server: OAuth2 and OIDC from Scratch"
date: 2026-09-22
tags: [Spring Security, OAuth2, OIDC, Java, Authorization Server, Spring Boot]
categories: [Java]
cover: "https://images.unsplash.com/photo-1774901128275-dcba96786383?w=1200&q=80&fit=crop&fm=webp"
description: Build a production-ready OAuth2/OIDC authorization server with Spring Authorization Server. Step-by-step guide with code examples for Java developers.
---

## Introduction

Setting up an OAuth2 and OpenID Connect (OIDC) authorization server has historically been one of the most daunting tasks in enterprise Java development. For years, developers relied on third-party libraries like Auth0, Okta, or self-hosted Keycloak to handle identity and access management. While these solutions work, they often introduce complexity, operational overhead, and vendor lock-in.

With the release of Spring Authorization Server, Spring has finally provided a first-class, lightweight, and highly customizable solution for building OAuth2 and OIDC servers directly within the Spring ecosystem. This isn't just another wrapper around Spring Security—it's a purpose-built module designed to handle the intricacies of token issuance, client registration, and standard compliance with minimal boilerplate.

In this post, we'll walk through building a fully functional OAuth2/OIDC authorization server from scratch using Spring Boot 3.x and Spring Authorization Server. We'll cover client registration, JWT signing, authorization code flow, and resource server integration. By the end, you'll have a production-ready foundation for securing your microservices architecture.

## Why Spring Authorization Server?

Before diving into code, let's understand why this module matters. Traditional Spring Security focused primarily on resource servers—protecting APIs from unauthorized access. However, it lacked native support for acting as an authorization server itself. Developers had to piece together multiple libraries or rely on external services.

Spring Authorization Server fills this gap by providing:
- Native support for OAuth2 and OIDC protocols
- First-class integration with Spring Security's authorization model
- Support for PKCE, JWT, and MTLS
- Extensible architecture for custom grant types and client registration
- Seamless integration with existing Spring Boot applications

The module is designed to be lightweight and opinionated enough to get you running quickly, yet flexible enough to handle enterprise-grade requirements.

## Project Setup and Dependencies

Let's start by creating a new Spring Boot project with the necessary dependencies. We'll need Spring Web, Spring Security, and the Spring Authorization Server starter.

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.security</groupId>
        <artifactId>spring-security-oauth2-authorization-server</artifactId>
        <version>1.2.4</version>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-oauth2-client</artifactId>
    </dependency>
</dependencies>
```

For this tutorial, we'll use Java 17+ and Spring Boot 3.2.x. Make sure your `pom.xml` or `build.gradle` reflects these versions. The Spring Authorization Server requires Java 17 or higher due to its dependency on modern Java features and Spring Security 6.x.

## Core Configuration: Authorization Server

The heart of our authorization server lies in the security configuration. Spring Authorization Server uses a fluent builder API to configure clients, scopes, and token settings. Let's create our main configuration class.

```java
@Configuration
@EnableWebSecurity
public class AuthorizationServerConfig {

    @Bean
    public SecurityFilterChain authorizationServerSecurityFilterChain(
            HttpSecurity http) throws Exception {
        OAuth2AuthorizationServerConfiguration.applyDefaultSecurity(http);
        
        http.getConfigurer(OAuth2AuthorizationServerConfiguration.class)
            .oidc(Customizer.withDefaults());
            
        return http.build();
    }
}
```

This basic configuration sets up the default endpoints for OAuth2 and OIDC, including:
- `/oauth2/token` for token requests
- `/oauth2/authorize` for authorization requests
- `/userinfo` for user info endpoint
- `/jwks.json` for public keys
- `/oidc/collection` for OpenID Connect discovery

However, this configuration alone doesn't handle client registration or token signing. We need to add more components.

## Client Registration and Scopes

In a real-world application, you'll have multiple OAuth2 clients (web apps, mobile apps, third-party integrations). Spring Authorization Server provides several ways to register clients, but for simplicity and flexibility, we'll use an in-memory client registration repository.

```java
@Bean
public RegisteredClientRepository registeredClientRepository() {
    RegisteredClient registeredClient = RegisteredClient.withId(UUID.randomUUID().toString())
        .clientId("my-web-app")
        .clientSecret("{bcrypt}$2a$10$...") // Encrypted secret
        .clientAuthenticationMethods(authMethods -> {
            authMethods.add(ClientAuthenticationMethod.CLIENT_SECRET_BASIC);
            authMethods.add(ClientAuthenticationMethod.CLIENT_SECRET_POST);
        })
        .authorizationGrantTypes(grantTypes -> {
            grantTypes.add(AuthorizationGrantType.AUTHORIZATION_CODE);
            grantTypes.add(AuthorizationGrantType.REFRESH_TOKEN);
            grantTypes.add(AuthorizationGrantType.CLIENT_CREDENTIALS);
        })
        .redirectUris(redirectUris -> {
            redirectUris.add("http://localhost:8080/login/oauth2/code/my-web-app");
            redirectUris.add("http://localhost:3000/callback");
        })
        .scopes(scopes -> {
            scopes.add("openid");
            scopes.add("profile");
            scopes.add("email");
            scopes.add("read");
        })
        .build();
        
    return new InMemoryRegisteredClientRepository(registeredClient);
}
```

Notice several important aspects here:
1. **Client IDs and Secrets**: Each client gets a unique ID and a securely stored secret. In production, you'd store these in a database rather than using `InMemoryRegisteredClientRepository`.
2. **Grant Types**: We're enabling authorization code flow (for interactive users), refresh tokens (for long-lived sessions), and client credentials (for machine-to-machine communication).
3. **Redirect URIs**: These must exactly match the URIs your clients will use. Any mismatch will result in authorization errors.
4. **Scopes**: We're defining standard OIDC scopes (`openid`, `profile`, `email`) plus a custom `read` scope. Scopes control what information the client can access.

## JWT Signing and Key Generation

OAuth2 tokens need to be signed to ensure their integrity. Spring Authorization Server supports both symmetric (HMAC) and asymmetric (RSA/EC) signing. For production, asymmetric keys are recommended because they allow resource servers to verify tokens without sharing secrets.

```java
@Bean
public KeyPair keyPair() {
    // In production, load these from a secure keystore
    RSAKey rsaKey = JwkGenerator.generateRsa();
    return new KeyPair(rsaKey.toRSAPublicKey(), rsaKey.toRSAPrivateKey());
}

@Bean
public JWKSource<SecurityContext> jwkSource() {
    RSAKey rsaKey = JwkGenerator.generateRsa();
    JWKSet jwkSet = new JWKSet(rsaKey);
    return (jwkSelector, context) -> jwkSelector.select(jwkSet);
}

private static class JwkGenerator {
    public static RSAKey generateRsa() {
        KeyPair keyPair = generateRsaKeyPair();
        RSAPublicKey publicKey = (RSAPublicKey) keyPair.getPublic();
        RSAPrivateKey privateKey = (RSAPrivateKey) keyPair.getPrivate();
        return new RSAKey.Builder(publicKey)
            .privateKey(privateKey)
            .keyID(UUID.randomUUID().toString())
            .build();
    }
    
    private static KeyPair generateRsaKeyPair() {
        try {
            KeyPairGenerator keyPairGenerator = KeyPairGenerator.getInstance("RSA");
            keyPairGenerator.initialize(2048);
            return keyPairGenerator.generateKeyPair();
        } catch (Exception ex) {
            throw new IllegalStateException(ex);
        }
    }
}
```

The `JWKSource` bean is critical—it tells the authorization server how to serve its public keys at the `/jwks.json` endpoint. Resource servers will fetch these keys to verify JWT signatures. In production, you should persist these keys and rotate them periodically.

## Resource Server Configuration

While this post focuses on the authorization server, it's important to understand how resource servers integrate with it. A resource server validates tokens and protects your APIs. Here's a minimal configuration:

```java
@Configuration
@EnableWebSecurity
public class ResourceServerConfig {

    @Bean
    public SecurityFilterChain resourceServerSecurityFilterChain(
            HttpSecurity http) throws Exception {
        OAuth2ResourceServerConfigurer resourceServer = 
            http.oauth2ResourceServer(OAuth2ResourceServerConfigurer::jwt);
            
        resourceServer.jwt(jwt -> 
            jwt.jwkSetUri("http://localhost:9000/oauth2/jwks"));
            
        http.authorizeHttpRequests(auth -> 
            auth.requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/private/**").authenticated()
                .anyRequest().denyAll());
                
        return http.build();
    }
}
```

The key line is `jwkSetUri`, which points to your authorization server's JWKS endpoint. This allows the resource server to fetch public keys and verify JWT signatures without sharing secrets.

## Testing the Authorization Server

Let's verify our setup works. First, start your authorization server on port 9000. Then, let's test the token endpoint using curl:

```bash
# Request an authorization code
# First, redirect the user to the authorization endpoint
curl -X GET "http://localhost:9000/oauth2/authorize?response_type=code&client_id=my-web-app&redirect_uri=http://localhost:8080/login/oauth2/code/my-web-app&scope=openid%20profile%20email&state=xyz"
```

This will redirect to your login page (which we haven't configured yet). For a simpler test, let's use the client credentials flow:

```bash
curl -X POST "http://localhost:9000/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=my-web-app" \
  -d "client_secret=your-client-secret" \
  -d "scope=read"
```

You should receive a JWT access token in the response. Verify it by decoding it at [jwt.io](https://jwt.io) using the public key from `http://localhost:9000/oauth2/jwks`.

## Production Considerations

While our example works for development, production deployments require additional considerations:

1. **Client Storage**: Replace `InMemoryRegisteredClientRepository` with a database-backed implementation. Spring Authorization Server provides `JdbcRegisteredClientRepository` out of the box.

2. **Token Store**: Similarly, use `JdbcOAuth2AuthorizationService` for persistent authorization records instead of in-memory storage.

3. **Key Management**: Store RSA/EC keys in a secure keystore (Java KeyStore, HashiCorp Vault, or AWS KMS). Implement key rotation strategies.

4. **HTTPS**: Never expose your authorization server over HTTP. All endpoints must use TLS 1.2+.

5. **PKCE**: For public clients (mobile apps, SPAs), enforce Proof Key for Code Exchange (PKCE) to prevent authorization code interception attacks.

6. **Rate Limiting**: Implement rate limiting on token endpoints to prevent abuse and brute-force attacks.

7. **Logging and Monitoring**: Add comprehensive logging for all authentication and authorization events. Integrate with monitoring tools like Prometheus and Grafana.

## Advanced: Custom Grant Types

One of Spring Authorization Server's powerful features is the ability to add custom grant types. For example, you might need to support a refresh token flow with additional validation or a device authorization grant for IoT devices.

```java
@Bean
public OAuth2AuthorizationServerConfigurer customGrantConfigurer() {
    return new OAuth2AuthorizationServerConfigurer() {
        @Override
        public void apply(HttpSecurity http) {
            http.oauth2ResourceServer(oauth2 -> oauth2.jwt(Customizer.withDefaults()))
                .authorizeHttpRequests(auth -> auth.anyRequest().authenticated());
        }
    };
}
```

Custom grants require implementing the `OAuth2TokenGenerator` and `OAuth2TokenValidator` interfaces, but this gives you complete control over the token issuance process.

## Key Takeaways

- **Spring Authorization Server** is the official, first-class solution for building OAuth2/OIDC servers in the Spring ecosystem
- **Client registration** should use persistent storage (database) in production, not in-memory repositories
- **Asymmetric key signing** (RSA/EC) is preferred over symmetric keys for production deployments
- **Resource servers** verify tokens by fetching public keys from the authorization server's JWKS endpoint
- **Security hardening** requires HTTPS, PKCE for public clients, rate limiting, and comprehensive logging
- **Custom grant types** are supported through extensible configuration, allowing you to implement proprietary flows
- **Testing** should be done with both interactive flows (authorization code) and machine-to-machine flows (client credentials)

Building an OAuth2/OIDC authorization server from scratch doesn't have to be painful. With Spring Authorization Server, you get a robust, standards-compliant foundation that integrates seamlessly with the rest of your Spring Boot applications. Start with the basics, iterate on security, and you'll have a production-ready identity provider in no time.