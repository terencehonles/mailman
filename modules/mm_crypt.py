try:
    from crypt import *
except ImportError:
    def crypt(string, seed):
        import md5
        m = md5.new()
        m.update(string)
        return m.digest()