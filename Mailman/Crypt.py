import mm_cfg

if mm_cfg.USE_CRYPT:
    from crypt import *
else:
    def crypt(string, seed):
        import md5
        return md5.new(string).digest()
