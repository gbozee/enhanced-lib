
trait SomeTrait:
    fn required_method(self,x:Int): ...

struct MyPair(SomeTrait):
    var first: Int
    var second: Int

    fn __init__(inout self, first: Int, second: Int):
        self.first = first
        self.second = second

    fn dump(self):
        print(self.first, self.second)

    fn required_method(self, x: Int):
        print("required_method", x)


fn greet(name: String) -> String:
    return "Hello, " + name + "!"

fn use_pair():
    let p = MyPair(1, 2)
    p.dump()
    fun_with_traits(p)

fn fun_with_traits[T: SomeTrait](x: T):
    x.required_method(42)
    repeat[3]("Hello")
    try:
        print_line()
    except:
        print("Error")

def print_line():
    long_text = "This is a long line of text that is a lot easier to read if"
            " it is broken up into multiple lines."
    print(long_text)


def do_math(x):
    var y = x + x
    y = y * y
    let z = y + x
    print(z)

fn repeat[count: Int](msg: String):
    for i in range(count):
        print(msg)


fn main():
    print("Hello, World!")
    print(greet("Alice"))
    try:
        do_math(23)
    except:
        print("Error")
    use_pair()
