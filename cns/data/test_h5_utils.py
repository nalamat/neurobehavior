import unittest
import h5_utils

class TestNode(object):
    
    def __init__(self, **kw):
        for v in kw.values():
            if isinstance(v, TestNode):
                v._v_parent = self
        self.__dict__.update(kw)

    def _f_walkNodes(self):
        for key, item in self.__dict__.items():
            if key != '_v_parent':
                yield item
                try:
                    for subitem in item._f_walkNodes():
                        yield subitem
                except AttributeError:
                    pass

    def _f_iterNodes(self):
        for key, item in self.__dict__.items():
            if key != '_v_parent':
                yield item

class TestWalkNodes(unittest.TestCase):

    def setUp(self):
        #s Emulates dummy node
        subnode_a = TestNode(x=4, y=5, z='hello', a='test')
        subnode_b = TestNode(a=7, x=4, y=6, z=TestNode(x=4, y=6, a='world'))
        subnode_c = TestNode(x=9, _v_attrs=TestNode(x='foo', bar='zoo'))
        self.node = TestNode(a=subnode_a, b=subnode_b, c=subnode_c, d=9)

    def test_rgetattr(self):
        attr = h5_utils.rgetattr(self.node, 'a')
        self.assertEquals(attr, self.node.a)
        attr = h5_utils.rgetattr(self.node, 'b.z.y')
        self.assertEquals(attr, 6)
        attr = h5_utils.rgetattr(self.node, 'c._v_attrs.x', strict=True)
        self.assertEquals(attr, 'foo')
        attr = h5_utils.rgetattr(self.node, 'c.bar', strict=False)
        self.assertEquals(attr, 'zoo')
        attr = h5_utils.rgetattr(self.node.b.z, '.a')
        self.assertEquals(attr, 7)
        attr = h5_utils.rgetattr(self.node.b.z, '..a.a')
        self.assertEquals(attr, 'test')
        attr = h5_utils.rgetattr(self.node.b.z, '.')
        self.assertEquals(attr, self.node.b)
        attr = h5_utils.rgetattr(self.node.b.z, '..')
        self.assertEquals(attr, self.node)

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
