from typing import Type

import registries


class Source:
    name: str = "error"
    pretty_name: str = "error"

    @staticmethod
    def default_sample_frequency():
        raise NotImplementedError("default_sample_frequency is not implemented")

    @staticmethod
    def default_record_length():
        raise NotImplementedError("default_record_length is not implemented")

    @staticmethod
    def augment_parser(parser):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass

    def read(self):
        raise NotImplementedError("read is not implemented")

    def data_range(self):
        raise NotImplementedError("read is not implemented")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_args):
        self.stop()
        self.close()


#
#
class SourceRegistry(registries.Registry[Type[Source]]):
    lookup_attrs = ('name',)

SOURCE_REGISTRY = SourceRegistry()
