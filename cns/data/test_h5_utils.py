import unittest
import h5_utils

class TestNode(object):
    
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def _f_walkNodes(self):
        for item in self.__dict__.values():
            yield item
            try:
                for subitem in item._f_walkNodes():
                    yield subitem
            except AttributeError:
                pass

    def _f_iterNodes(self):
        for item in self.__dict__.values():
            yield item
        
class TestWalkNodes(unittest.TestCase):

    def setUp(self):
        #s Emulates dummy node
        subnode_a = TestNode(x=4, y=5, z='hello')
        subnode_b = TestNode(x=4, y=6, z=TestNode(x=4, y=6, a='world'))
        subnode_c = TestNode(x=9, _v_attrs=TestNode(x='foo'))
        self.node = TestNode(a=subnode_a, b=subnode_b, c=subnode_c)

    def assertNumNodes(self, iterable, num_expected):
        num_actual = len(list(iterable))
        self.assertEquals(num_actual, num_expected)

    def testIterNodes(self):
        self.assertNumNodes(h5_utils.iter_nodes(self.node, {'x': 4}), 2)
        self.assertNumNodes(h5_utils.iter_nodes(self.node, {'y': 6}), 1)
        self.assertNumNodes(h5_utils.iter_nodes(self.node, {'z': 'world'}), 0)
        self.assertNumNodes(h5_utils.iter_nodes(self.node, {'a': 'world'}), 0)
        self.assertNumNodes(h5_utils.iter_nodes(self.node, {'z.a': 'world'}), 1)
        self.assertNumNodes(h5_utils.iter_nodes(self.node, {'_v_attrs.x': 'foo'}), 1)

        # This filter matches the *root* node, which should never be returned in
        # an iterable
        self.assertNumNodes(h5_utils.iter_nodes(self.node, {'b.z.a': 'world'}), 0)

        # Just making sure we're getting the right node back (e.g. node.b as
        # opposed to node.b.z or node.b.z.a)
        nodes = h5_utils.iter_nodes(self.node, {'z.a': 'world'})
        self.assertEquals(list(nodes), [self.node.b])

        nodes = h5_utils.iter_nodes(self.node, {'_v_attrs.x': 'foo'})
        self.assertEquals(list(nodes), [self.node.c])

    def testWalkNodes(self):
        self.assertNumNodes(h5_utils.walk_nodes(self.node, {'x': 4}), 3)
        self.assertNumNodes(h5_utils.walk_nodes(self.node, {'y': 6}), 2)
        self.assertNumNodes(h5_utils.walk_nodes(self.node, {'a': 'world'}), 1)

if __name__ == '__main__':
    unittest.main()
