from main import create_user, get_user_index, get_link, load_user_dict, load_user_link

TEST_ID = 123

def test_create_user():
	result = create_user(TEST_ID)
	print(result)

def test_get_user_index():
	result = get_user_index(TEST_ID)
	print(result)

def test_get_link():
	result = get_link(TEST_ID)
	print(result)

def test_load_user_dict():
	result = load_user_dict()
	print(result)

def test_load_user_link():
	result = get_link(TEST_ID)
	print(result)

if __name__ == "__main__":
	test_create_user()


