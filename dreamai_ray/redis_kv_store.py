import redis
from wasabi import msg


def connect_to_server(redis_host="127.0.0.1", redis_port=6379):
    try:
        r = redis.StrictRedis(
            host=redis_host, port=redis_port, charset="utf-8", decode_responses=True
        )
    except Exception as e:
        raise Exception(f"Connecting to Redis Server failed with error {e}")
    return r


class KeyValueStore:
    def __init__(self, redis_host="127.0.0.1", redis_port=6379):
        try:
            self.server = connect_to_server(redis_host=redis_host, redis_port=redis_port)
            # self.logger = logger
        except Exception as e:
            raise

    def insert(self, key, value):
        server = self.server
        # ogger.debug(key,value)
        msg.info(key, value, spaced=True)
        server.hmset(key, value)

    def get(self, key):
        server = self.server
        # logger.debug(key)
        try:
            val = server.hgetall(key)
        except Exception as e:
            # logger.error("unable to retrieve value of key {} from Redis: error = {}".format(key,e))
            raise f"Unable to retrieve value of key {key} from Redis: error = {e}"
        return val

    def getall(self):
        return self.server.keys()

    def remove(self, key):
        server = self.server
        # logger.debug('removing key {}'.format(key))
        msg.info("removing key {}".format(key), spaced=True)
        try:
            all_keys = list(server.hgetall(key).keys())
            server.hdel(key, *all_keys)
            # logger.debug('key {} removed'.format(key))
            msg.info("key {} removed".format(key), spaced=True)
        except Exception as e:
            # logger.error("unable to remove key {} from Redis: error = {}".format(key,e))
            raise f"Unable to remove key {key} from Redis: error = {e}"
