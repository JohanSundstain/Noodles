import time

from servers import server_manager

# ----------------------------
# НАСТРОЙКИ
# ----------------------------

TEST_USER = "test_user_12345"


# ----------------------------
# TEST
# ----------------------------

def test_api():

    client =server_manager.get_api_server("kz-1")

    print("\n=== CREATE USER ===")
    result = client.create_user(TEST_USER)
    print(result)


    time.sleep(2)


    print("\n=== CHECK EXISTS ===")
    result = client.user_exists(TEST_USER)
    print(result)


    time.sleep(1)


    print("\n=== GET LINK ===")
    result = client.get_link(TEST_USER)
    print(result)


    time.sleep(1)


    print("\n=== GET TEMP LINK ===")
    result = client.get_temp_link(
        TEST_USER,
        seconds=60
    )
    print(result)


    time.sleep(1)


    print("\n=== DELETE USER ===")
    result = client.delete_user(
        [TEST_USER]
    )
    print(result)


    time.sleep(2)


    print("\n=== CHECK AFTER DELETE ===")
    result = client.user_exists(TEST_USER)
    print(result)



if __name__ == "__main__":
    test_api()