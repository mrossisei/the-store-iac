import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
from acceso_kind import AccessError
spec=importlib.util.spec_from_file_location('app_operator',Path(__file__).parents[1]/'scripts/aplicacion.py')
operator=importlib.util.module_from_spec(spec);spec.loader.exec_module(operator)


class PlanBoundaryTests(unittest.TestCase):
    def plan(self,address,kind,actions):
        return {'resource_changes':[{'mode':'managed','address':address,'type':kind,'change':{'actions':actions}}]}

    def test_normal_apply_cannot_destroy_deployment_or_touch_aws(self):
        for plan in (self.plan('module.app_a[0].kubernetes_deployment_v1.service["ui"]','kubernetes_deployment_v1',['delete']),self.plan('aws_iam_role.foreign','aws_iam_role',['create'])):
            with self.assertRaises(AccessError):operator.review(plan)

    def test_quarantine_can_remove_allows_without_destroying_pods(self):
        self.assertEqual(operator.review(self.plan('module.politicas_b[0].kubernetes_network_policy_v1.edge["checkout-orders"]','kubernetes_network_policy_v1',['delete'])),{'delete':1})

    def test_destroy_rejects_plan_that_creates_or_updates(self):
        with self.assertRaises(AccessError):operator.review(self.plan('module.app_a[0].kubernetes_deployment_v1.service["ui"]','kubernetes_deployment_v1',['update']),destroying=True)
