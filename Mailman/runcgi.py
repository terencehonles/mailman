from Mailman.debug import *

def wrap_func(func, debug=1, print_env=1):
    if not debug:
      try:
          sys.stderr = mm_utils.StampedLogger("error", label = 'admin',
                                    manual_reprime=1, nofail=0)
      except:
          # Error opening log, show thru anyway!
          wrap_func(func, print_env=print_env, debug=1)
          return
      func()
      return
    else:
      try:
        func()
      except SystemExit:
        pass
      except:
        print_trace()
        if print_env:
           print_environ()

