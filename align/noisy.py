import pymeasure
import pymeasure.adapters

class NoisyPrologixAdapter(pymeasure.adapters.PrologixAdapter):
    def __init__(self, *args, **kwargs): super().__init__(*args, **kwargs)

    def write(self, command, **kwargs):
        print(f"-> \"{command}\" {kwargs}")
        super().write(command, **kwargs)

    def read(self, *args, **kwargs):
        print(f"<- ", end="")
        result = super().read(*args, **kwargs)
        print(f"\"{result}\"")
        return result
