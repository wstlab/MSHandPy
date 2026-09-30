def schedule(func, arg):
    func(arg)

def const(x):
    return x

def mem_info(verbose=False):
    print("Memory info:")
    print("  Available: 128KB")
    print("  Used: 32KB")

def qstr_info():
    print("QSTR info: 100 strings")