try:
    from crypt import *
except ImportError:
    def crypt(string, seed):
        import md5
        return md5.new(string).digest()
