Feature: Copy User Address Data into Form Workflow (KAN-95)
  As a customer
  I want my profile address to be copied into form drafts
  So that I don't have to manually re-enter my address information

  Background:
    Given the customer notification system is running
    And the address copy endpoints are available

  Scenario: Successfully copy address from profile to form draft
    Given a customer with ID "customer-123" is authenticated
    And the customer has an address in their profile:
      | field       | value           |
      | street      | 123 Main St     |
      | city        | Springfield     |
      | state       | IL              |
      | postal_code | 62701           |
      | country     | USA             |
    When the customer requests to copy address to draft "draft-001"
    Then the response status should be 200
    And the response should contain the draft ID "draft-001"
    And the response should contain status "copied"
    And the copied address should match:
      | field       | value           |
      | street      | 123 Main St     |
      | city        | Springfield     |
      | state       | IL              |
      | postal_code | 62701           |
      | country     | USA             |

  Scenario: Copy default empty address when no address exists in profile
    Given a customer with ID "customer-456" is authenticated
    And the customer has no address in their profile
    When the customer requests to copy address to draft "draft-002"
    Then the response status should be 200
    And the response should contain the draft ID "draft-002"
    And the response should contain status "copied"
    And the copied address should be empty with defaults:
      | field       | value |
      | street      |       |
      | city        |       |
      | state       |       |
      | postal_code |       |
      | country     |       |

  Scenario: Unauthorized request returns 401 with ProblemDetail format
    Given a customer is not authenticated
    When the customer attempts to copy address to draft "draft-003"
    Then the response status should be 401
    And the response should follow RFC 7807 ProblemDetail format
    And the problem detail should contain:
      | field    | value                                                           |
      | title    | Unauthorized                                                    |
      | status   | 401                                                             |
      | detail   | Authentication credentials were not provided or are invalid.    |
      | instance | /forms/draft-003/address:copyFromProfile                        |

  Scenario: Get customer address endpoint returns stored address
    Given a customer with ID "customer-789" is authenticated
    And the customer has an address in their profile:
      | field       | value           |
      | street      | 456 Oak Ave     |
      | city        | Portland        |
      | state       | OR              |
      | postal_code | 97201           |
      | country     | USA             |
    When the customer requests their address from profile
    Then the response status should be 200
    And the returned address should match:
      | field       | value           |
      | street      | 456 Oak Ave     |
      | city        | Portland        |
      | state       | OR              |
      | postal_code | 97201           |
      | country     | USA             |

  Scenario: Get customer address endpoint requires authentication
    Given a customer is not authenticated
    When the customer attempts to retrieve their address
    Then the response status should be 401
    And the response should follow RFC 7807 ProblemDetail format
    And the problem detail title should be "Unauthorized"
