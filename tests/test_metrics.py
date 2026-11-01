"""손계산과 대조하여 여러 역 합산·인구 분모·재실행을 검증합니다."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import networkx as nx
from common import gravity,weighted_mean,SPEED
from analyze import calculate_scores

class MetricsTest(unittest.TestCase):
    def test_hand_calculation(self):
        self.assertAlmostEqual(gravity([0,10,30,31]),1+.5+.125)
        self.assertEqual(gravity([31,100]),0)
    def test_population_denominator(self):
        self.assertAlmostEqual(weighted_mean([100,300],[1,0]),.25)
        self.assertTrue(np.isnan(weighted_mean([100,300],[1,np.nan])))
        self.assertTrue(np.isnan(weighted_mean([0],[0])))
    def test_multistation_and_reexecution(self):
        g=nx.Graph();g.add_edge(1,2,length=10*SPEED);g.add_edge(2,3,length=20*SPEED)
        args=(g,np.array([1]),np.array([0.]),np.array([1,2,3]),np.zeros(3))
        score,_,counts=calculate_scores(*args)
        self.assertAlmostEqual(score[0],1+.5+.125)
        self.assertEqual(counts[0],3)
        again,_,_=calculate_scores(*args)
        np.testing.assert_array_equal(score,again)
    def test_same_node_different_stations(self):
        g=nx.Graph();g.add_node(1)
        score,_,_=calculate_scores(g,np.array([1]),np.zeros(1),np.array([1,1]),np.zeros(2))
        self.assertEqual(score[0],2)
    def test_connector_distances_and_failure(self):
        g=nx.Graph();g.add_edge(1,2,length=8*SPEED)
        score,_,_=calculate_scores(g,np.array([1,1]),np.array([SPEED,301]),np.array([2]),np.array([SPEED]))
        self.assertAlmostEqual(score[0],.5)
        self.assertTrue(np.isnan(score[1]))

if __name__=='__main__': unittest.main()
