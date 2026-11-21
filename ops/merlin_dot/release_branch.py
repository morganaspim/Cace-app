"""Fixed private release from one accepted full-native source and retained original-task assessment receipt.

This replaces the old three-file additive controller at its existing path. The
private service, grant profile and canonical state are not reconfigured/reseeded.
The retained assessment runs separately; validate/deploy/inspect never invoke a model.
"""
import base64
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile
import zipfile
PINS={'assessment': {'expected_context_fetch_sha256': '1751f1b501bb2bd0db2489c09ce9bff12c7ef6d5dc3c88fe1170825e2d3123e7', 'expected_handoff_result_sha256': '90d07dfbc795c2bff0a5c2b3b2a6c02af87f36a8bc5cf1dbb8be04c54848333d', 'invocation': {'request_id': '58605b90-c39d-4479-9c90-623b27056d92', 'run_attempt': 1, 'run_id': 44923397429, 'workflow_commit': '9918a8d1a32d5768d74789c117ec235cd5d8106b'}, 'provider_files': {'bootstrap': '7b7489297414d8304f12e8c0e28aec8ddd806704889f8b17986eac8ada0cba57', 'manifest': '35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203'}, 'provider_revision': 'gguf:cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046;llama:2a4daf0e08d6a9b6993ee0d4a9a3cfc35a6f405c;bin:af4c10f1f4a1e7f0878dc9b3896bb742f65170861276ef04ddecdf2a9be3cd82', 'ref': {'logical_path': 'local-research/merlin-exact-assessment-20261121/host/receipt.json', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '8d1760812d9e15f9e15f525de6f383b36e285646a25b26b710a48181ff12644d', 'version': 1}, 'refs': {'assessment_report_ref': {'logical_path': 'local-solver/merlin-exact-assessment-20261121/report.json', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '1ac7c99f3d149ec92ec6df2eba7e0aff82238afd436b6bf5d38f96f0c711f0e5', 'version': 1}, 'handoff_ref': {'logical_path': 'handoffs/merlin-exact-assessment-20261121.json', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '0cf1f065e22cb1c564855728bf56773cff0d786f39c5c191f6962da721b77c46', 'version': 1}, 'provider_bootstrap_ref': {'logical_path': 'local-research/merlin-exact-assessment-20261121/host/provider-bootstrap.json', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '7b7489297414d8304f12e8c0e28aec8ddd806704889f8b17986eac8ada0cba57', 'version': 1}, 'provider_manifest_ref': {'logical_path': 'local-research/merlin-exact-assessment-20261121/host/provider-manifest.json', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203', 'version': 1}, 'report_source_ref': {'logical_path': 'context/merlin/1a427c7df1c15cdcae601f7daa6ac4b0431983f8cb455ce9cf56d9bd436b2a38/source.txt', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '1ac7c99f3d149ec92ec6df2eba7e0aff82238afd436b6bf5d38f96f0c711f0e5', 'version': 1}, 'research_plan_ref': {'logical_path': 'local-research/merlin-exact-assessment-20261121/host/research-plan.json', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '33eb59790eaaddb860ca399657e0d0b52acd0ff201a3a53ce23e0df456c023bb', 'version': 1}, 'retained_inputs_ref': {'logical_path': 'local-research/merlin-exact-assessment-20261121/host/retained-inputs.json', 'project_id': 'dot-production-docs', 'schema': 'merlin-artifact-ref/1', 'sha256': '8f7a13740d46e2bb0150ffc365e7485ae463a1a158d2bb0221d60e424c1642f2', 'version': 1}}, 'report_bytes': 6481, 'report_sha256': '1ac7c99f3d149ec92ec6df2eba7e0aff82238afd436b6bf5d38f96f0c711f0e5'}, 'native': {'artifact_bytes': 650520, 'artifact_id': 14712858088, 'artifact_sha256': '8c0f034e899dc73ac6731f802a2f390aa1c80eb37c2f1216968da709a081598d', 'controller_git_blob': 'cf612303b8b74f91ff6eddec7dfcf1f32eb3a3c5', 'controller_sha256': '58d07437d683b617d8452af666025ace74b0395a7fa26708fc0423a4b468e258', 'report_sha256': 'b187142c4f522a3d4876f66a10c2d5792ee2b146e8d3a952e36bfe1e3755f43d', 'run_attempt': 1, 'run_id': 44919201279, 'software_tests': 599, 'source_package_sha256': '31afbda693cfcbe75bdfa56a3b47571271c7a6e817fd1264a56d6f23930da4ad', 'test_inventory_sha256': '8fea9b239870559acc888ddd7d003d8754234dfa1f8497020de5dc108c8cfd4b', 'workflow_commit': 'c1c901f320f45f4ed6b9b93fb886b18ffeb25bcf', 'workflow_git_blob': '86f5f0bb48d61972d778d078922cdb9855d49851'}, 'provider_inspector': {'git_blob': '67c699c2f27c1acfdc202eeed5b0468cb12ae029', 'sha256': 'f47637659c5d71e5d75cdb7198a0e07092a69f1b7857d45c92fa19be40bd8fa5'}, 'runtime_files': {'python/dot_ai_os/__init__.py': '5a54db6fddc5b1a178c7beaa42089ee95bdea81871560c8c5d1f868a2b16e487', 'python/dot_ai_os/bridge.py': '781447bcfb965e11b39d7cedfc1d4f1db3c6c67f502bffc6a07605af7cf085a3', 'python/dot_ai_os/dual_coder.py': '5c28a7fd3d7183d4c1e75123784c7d25fb73d9cbc04363f60076031e55591fdd', 'python/dot_ai_os/fixed_solver_worker.py': '7f0947df45c3239cce48dd7e112886f4ccff98dd097673d0275844d227caf8f6', 'python/dot_ai_os/job_inbox.py': '3c4f1fdd6a6d97dc5288f892e9c8a592816449c80a3e7f77afa3105e9bf1bcf8', 'python/dot_ai_os/local_research.py': 'ca105f28567655679d771db1151e80b2b54811fb30d9cc6214cee9fb133aea42', 'python/dot_ai_os/math_lenses.py': 'd8a5206a2fa55dbe132c1d6da57cfb958d5899a3d19d8c1c1c03726f98aaee3d', 'python/dot_ai_os/private_runtime.py': '7e6538e04ef503b7c595727d59a1650a8a1c3fab1ba17a6e63df8017eed5849c', 'python/dot_ai_os/research_protocol.py': 'ff976d8c45f4f9683caaeefe46b0eecf40404c2f37d84945460c93a1a255cc98', 'python/dot_ai_os/research_tools.py': '9976f94df42d08f2b36f6e820f78c39019a571049e5b99612e73f89b75380fd4', 'python/dot_ai_os/simulation_research.py': '8c39f2a609b01fbf573fe83c9ccedfab534f0dd2bf769f916a66b0241b599d9d', 'python/merlin/__init__.py': '49f23ffa9b838de063cd88e4a60704d1989f55ff3aa70fe2ed850b0396fa8f93', 'python/merlin/artifact_ref.py': '187e33ed4ab6e1a79e054ff31c07b383090dae94cb51c5eb9dd01dfb80227584', 'python/merlin/branch_research.py': '29f69cc519a684ae5315a5eead0651a5ccf5040ce52e582a0d93355ada806af7', 'python/merlin/council.py': 'bb1c1827e96087a5aff4b4b780efef791780a9c7be42d9f561a1a14cd77d9cd0', 'python/merlin/council_runtime.py': '9299f556db15fd8ddfc6b1d18e2d949a94d38bfdd8e6b52ab33fddc07f10747c', 'python/merlin/engineering_ir.py': '1c5a478525bb4cf1b49b848196278b3c5e7b4b477a315525dca08a6dd1f9990f', 'python/merlin/event_outbox.py': 'ccc1ec2e8d069686607365ba122b4a45e3118a628c5c4f288705c73e6468ceb2', 'python/merlin/hermes_process.py': 'e89c80659172b22f6db73dbe00abc880aa80bf4e4895801c5501a59b7fbd08b3', 'python/merlin/hermes_systemd.py': '68f260786aed0193c0c9d655ee0b316d35b519d97f7bd0b424bbebde1b2b7c98', 'python/merlin/hermes_worker.py': '0047e687cab9577467abbae724a5dddc0905cc3eb4c6486d5efffbaab14017ac', 'python/merlin/project_registry.py': 'c7fbd89ae99705f60a1ecd7f41df244742fe218a335b4a3e6d2fed11c96521c7', 'python/merlin/scientific_loop.py': '8271072d8174336fc9bd3e60ede294ce08a0ccbda5d9ff75fa584dc75220e574', 'python/merlin/telemetry.py': '15539c20ffc8fb36b01f745e25d453955bccacea95d7d47940e9777302ede59c', 'python/merlin/weight_binding.py': 'f6927e5860fc6adbcd034f4889c0e3a89625a58ab74c3dbbcffb305cb0e6e047'}, 'source_commit': '761756025fb88f7e722c799ca91964e3ad24c53a', 'source_files': {'python/dot_ai_os/__init__.py': '5a54db6fddc5b1a178c7beaa42089ee95bdea81871560c8c5d1f868a2b16e487', 'python/dot_ai_os/bridge.py': '781447bcfb965e11b39d7cedfc1d4f1db3c6c67f502bffc6a07605af7cf085a3', 'python/dot_ai_os/dual_coder.py': '5c28a7fd3d7183d4c1e75123784c7d25fb73d9cbc04363f60076031e55591fdd', 'python/dot_ai_os/fixed_solver_worker.py': '7f0947df45c3239cce48dd7e112886f4ccff98dd097673d0275844d227caf8f6', 'python/dot_ai_os/job_inbox.py': '3c4f1fdd6a6d97dc5288f892e9c8a592816449c80a3e7f77afa3105e9bf1bcf8', 'python/dot_ai_os/local_research.py': 'ca105f28567655679d771db1151e80b2b54811fb30d9cc6214cee9fb133aea42', 'python/dot_ai_os/math_lenses.py': 'd8a5206a2fa55dbe132c1d6da57cfb958d5899a3d19d8c1c1c03726f98aaee3d', 'python/dot_ai_os/private_runtime.py': '7e6538e04ef503b7c595727d59a1650a8a1c3fab1ba17a6e63df8017eed5849c', 'python/dot_ai_os/research_protocol.py': 'ff976d8c45f4f9683caaeefe46b0eecf40404c2f37d84945460c93a1a255cc98', 'python/dot_ai_os/research_tools.py': '9976f94df42d08f2b36f6e820f78c39019a571049e5b99612e73f89b75380fd4', 'python/dot_ai_os/simulation_research.py': '8c39f2a609b01fbf573fe83c9ccedfab534f0dd2bf769f916a66b0241b599d9d', 'python/merlin/__init__.py': '49f23ffa9b838de063cd88e4a60704d1989f55ff3aa70fe2ed850b0396fa8f93', 'python/merlin/academic_source_store.py': '1dd96408e64519a2ce5b36c74f8f0cca780ba1f2eb373321a02b730cb25a49dd', 'python/merlin/app.py': 'abb39e2f289dc3ad117abf91a47947ea0200cd43e1db5dfb795a7c70ff63a33b', 'python/merlin/artifact_ref.py': '187e33ed4ab6e1a79e054ff31c07b383090dae94cb51c5eb9dd01dfb80227584', 'python/merlin/branch_registry.py': 'ee4cfbf76fa4eaedf86085e74435b2022bf02a10074204aab60422534ef34eb0', 'python/merlin/branch_research.py': '29f69cc519a684ae5315a5eead0651a5ccf5040ce52e582a0d93355ada806af7', 'python/merlin/branch_task_recovery.py': 'af5871152c49079f00ee15fdeb51f189280d6efd780ffbeecbd55c75d3e22512', 'python/merlin/build_admission.py': '13e86b320deb293365c47860cff23e05439587aabad988d707042dfc15809500', 'python/merlin/build_loop.py': '9c5bc987af35f5da613c439459e5e6dcae7fc415e23d597a99cc4603845b6732', 'python/merlin/cace_adapter.py': '7f1385f3be48078358d6fd677335a2253c5fc8d558dbb8965c10ad31cd19c3cc', 'python/merlin/cace_attestation.py': '8f2bd4c03eb576ce7161a0a6ede6b718d206e07f015faa3cee16e119ab0326b2', 'python/merlin/capability_registry.py': '3911648b27a86e7402aba7ccd719bf8240856dbf8ee8283a2b717dd57663df8f', 'python/merlin/council.py': 'bb1c1827e96087a5aff4b4b780efef791780a9c7be42d9f561a1a14cd77d9cd0', 'python/merlin/council_runtime.py': '9299f556db15fd8ddfc6b1d18e2d949a94d38bfdd8e6b52ab33fddc07f10747c', 'python/merlin/engineering/__init__.py': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'python/merlin/engineering/geometry.py': '3329684f672508c3b2d6ddb1f8b5c1f80b075aed6598b04e6ad549c540113d2e', 'python/merlin/engineering/netlist.py': '81cd6c94ca4ba6ec6c345f5a113804de082f35fc5b4a702cb9277f105091761a', 'python/merlin/engineering_ir.py': '1c5a478525bb4cf1b49b848196278b3c5e7b4b477a315525dca08a6dd1f9990f', 'python/merlin/event_outbox.py': 'ccc1ec2e8d069686607365ba122b4a45e3118a628c5c4f288705c73e6468ceb2', 'python/merlin/hermes_claim_routing.py': 'a35db4516b47a1f6374810449db36b076de689b1e7dcf65d5085034a07af29ec', 'python/merlin/hermes_outbox.py': '3a6f10491090788349507f4224624ff93df0b20386b62c706b1351559a2b4008', 'python/merlin/hermes_process.py': 'e89c80659172b22f6db73dbe00abc880aa80bf4e4895801c5501a59b7fbd08b3', 'python/merlin/hermes_proof_orchestrator.py': '6da5980e4e58b901623bc2270c9ddcfdde3c200ac49c7faffe302317a6cd745d', 'python/merlin/hermes_stage_handlers.py': 'ba775b5c93e90bad45d35300fab9eac92588a6bcd6725113422eea9f6ef159fb', 'python/merlin/hermes_stage_journal.py': '40557d275160ae4709b77bf8fcab3377fdfec1e04c700b36788552572fd1d721', 'python/merlin/hermes_systemd.py': '68f260786aed0193c0c9d655ee0b316d35b519d97f7bd0b424bbebde1b2b7c98', 'python/merlin/hermes_worker.py': '0047e687cab9577467abbae724a5dddc0905cc3eb4c6486d5efffbaab14017ac', 'python/merlin/hud_activity.py': '7bde1957d74bfedf69df7144bada6029bf022d08f506477c96bf401ef4cee452', 'python/merlin/hud_http.py': '97dda66983a8e98241aa0a00e06658587f2e8f237be8b746eddbf5bb386f14e4', 'python/merlin/hud_objects.py': 'ba44c444970ad349a8dbff93b597d3cf7906cf6d432b0901ae802cbf1255ec7d', 'python/merlin/hud_runtime.py': 'a3bc89abcf20f90e20f239c91743d0d24e3a16dc16539c621a33d32c87438df3', 'python/merlin/hypothesis_ledger.py': 'b9e80136d0f1e4f31ea61e9f2a9e60d768d99595f46e9a2b916eaa8398f89755', 'python/merlin/identity.py': 'c8f7c353de0b2b485b6fc72c67c30e7a75f233443380ba58375941d273c64444', 'python/merlin/ideonomy.py': '96b28b5b59591f067ffe609fdf1f5a2d085822f8d2c5f5148e1d4ea1b4a7ae41', 'python/merlin/intent_compiler.py': 'e9646959224866e12657c3be2787dbdd015921d73ef49e6cac7cf0943eff3fd1', 'python/merlin/interaction_learning.py': 'ff7ca67aa54814069c408b97b0ad23aa4ebcb8deee9c86302d8cf4d3ac956e29', 'python/merlin/knowledge_compression.py': 'a1df44cd12cb4d56ea2f974c7b3ab4a507c38d06344f69ad373b4e1a90b95ce2', 'python/merlin/knowledge_graph.py': '75e3795fda13dc3efe0e60da8aff702b7a44fe21cbadd50c7f06fc9dfd99c06c', 'python/merlin/knowledge_reconstruction.py': '11fefd3cf18640ea6475767352a53e9eb797d379a9a5eb839bb8e63558d85f14', 'python/merlin/learner_model.py': 'a36a164860763687d4a0be2b5749165d016f968ac9180736e19bf7936a8a2dbb', 'python/merlin/learning_evidence.py': '2f952fc9645835d77f96d8725e64960879717b58f57762cd5430874dc712ea80', 'python/merlin/learning_evidence_eval.py': '35af69016b113270063db6dc84d6f3e2c7bcd1eba6681483c212807812709966', 'python/merlin/learning_lab_bridge.py': 'b80966b5c06fd04cc7a9b01772b91451a0f3edcaa26786aff40531f00b3546d2', 'python/merlin/learning_platform.py': 'e706a5830d6bb9d9f709ea39107264749d410eb4a640623aa877efdf8aaaf0e0', 'python/merlin/learning_research_api.py': 'bd212b7450d1cafae455a3f77c17549d0f47412489484f189a125a3b8bd8c4d3', 'python/merlin/learning_research_config.py': '044040ff69aa2c11e7a6cc4c442fb87c25b0c2e0b075e13df2b78bbcb91f906f', 'python/merlin/learning_titan_course.py': 'd9f5ea57b4216416d044d19ed73aded64057152073b4d3748062d7755ae9c12e', 'python/merlin/linear_simulation.py': 'cb4ade5b883536b7ca01762ec091c43916b5e07f18bb4739cf42a90e069d15f9', 'python/merlin/logos_review.py': 'f970e8867381e9a10592efaf9174174095f0c0c9df7178e36331ef60e4ccfb55', 'python/merlin/math_algebra_functions_course.py': 'f96a6ad530b0d87d1390e770b9a4661208b2e100f5949b3fbc7bf8cac4debdab', 'python/merlin/math_calculus_probability_course.py': '238951d9372539ed678f26a0755affa133f3a9281b1e6c8690addc626f5f6449', 'python/merlin/math_foundations_course.py': 'da312414ec360cb0f5b6fc72657511398dc9be077d0e3321d0c56248a20be353', 'python/merlin/math_logic_discrete_course.py': '84bb2784522e4044a21eae1c1e20808bafa42872fbc13edfb1645f710e67e795', 'python/merlin/math_numerical_scientific_computing_course.py': '45ab5e3d3b8b6430eeaa780289c6c93da7d532f90c64ae314a9f06f47dec2981', 'python/merlin/math_transfer.py': '0b75c695206ac98cc211457b33aa2b61fae082f80df2b23e1d5c84aa6308794a', 'python/merlin/memory_vault.py': '53384296dedc3b615dd7df865e5153d93dab6b57578f2321e8ec39b1b48bb171', 'python/merlin/ngspice_engine.py': 'e951ce53c6092648072d8a8be0015a59f5e9fb80efa314bd3e7ee1926f8bb525', 'python/merlin/packet_process.py': 'a63944a4db2d2068383eb200990b62ab5620b2c0c07379d95f480a7449f8e886', 'python/merlin/project_registry.py': 'c7fbd89ae99705f60a1ecd7f41df244742fe218a335b4a3e6d2fed11c96521c7', 'python/merlin/prompt_contract.py': 'd83259bf229da275d50a612bdfd63adf804d5c671284032a4f5ee6d85f92b3b8', 'python/merlin/public_literature.py': '53f70b4fb3adfbb5ebe44c558fbcea1fbb2b0351f8f4978b9a5ff3da6978c01f', 'python/merlin/registry_queries.py': '8ece661b8f9e5a4bb159b68b3e63182a346e8872bf0106434b12cb580459f366', 'python/merlin/research.py': 'ddf9978063e38c05f4a0b8224bdd35a2a7e5045d80ec1e0ac5adeb7d8b3be19d', 'python/merlin/research_curriculum.py': 'f80b626eb9bf280ffaa061332f871818bcf4d8eb3d17fd501d3e1252256d6d87', 'python/merlin/research_evidence.py': 'ca63be784cf8e8d787500c981bfc5018c7c8f570db2b535a277590cbb0a4eb18', 'python/merlin/research_lifecycle.py': 'a2701c0a3cc2cb2151e3b307491b584ddbdb1c0f2454ff4d3050ab021d375447', 'python/merlin/review_context.py': '82d534a447d26030fe9808eaf56543eee0027fc21c6e8a5ec0e21e05b5f61bef', 'python/merlin/scientific_loop.py': '8271072d8174336fc9bd3e60ede294ce08a0ccbda5d9ff75fa584dc75220e574', 'python/merlin/simulation.py': '350abcc883b1586e8d356597842bf41d2589d8bf255b1e428da0c154a2c7dc4a', 'python/merlin/telemetry.py': '15539c20ffc8fb36b01f745e25d453955bccacea95d7d47940e9777302ede59c', 'python/merlin/telemetry_graph.py': '77f658bd99d8e9cda92e7da3460db794dfb52273a490848fb7b084d6043ac6c3', 'python/merlin/text_extractor.py': '1b5f397721beaffd05e2f1053741c7e24261e18a1f71025d9617781f0982b923', 'python/merlin/titan_crypto_lab.py': '663fbf3e3a24c2818c4e31f28d1bdbae056e6387d9cb24d97bd8227f6d5c0381', 'python/merlin/titan_protocol_model.py': 'c96802f62cfc1cc16d3a35ca3a1adf4d13978077b32cea8e51d0e57275ec0a98', 'python/merlin/virtual_repository.py': 'd664e392a81ad7b50b73acc4f29cc74987f97f532efe45ca6f93ff5efebe1b53', 'python/merlin/virtual_repository_seed.py': '0535fbcc13a4a4ecd0abac9b894c1dd0e4c2d99d456ee05a9ccc798ea849ced4', 'python/merlin/weight_binding.py': 'f6927e5860fc6adbcd034f4889c0e3a89625a58ab74c3dbbcffb305cb0e6e047', 'scripts/merlin/oci_cgroup_drill.py': '578fbba1e8ac8dc081e8a9a7734310be6e85bcc7278c1bf92c9fa6a2794367b3', 'scripts/merlin/oci_review_context_drill.py': 'f4f7de65086f9caf57a81424b87035eb2abc4c75f949d8dbd995f3a126524aa4', 'tests/fixtures/learning-evidence-eval-v1.json': 'b6b6b28f3aaea631c78fc7e06a23ca0d5d4342cfc065a3887f451f18a942b018', 'tests/test_app_model_transport.py': '1c953dec1eefec35de03eee383783ee235c0df968b43c06764a4b71205881710', 'tests/test_branch_registry.py': 'e8730a88684fdff20d5ae735b126478db40e41bf169fdd29574cfd8c9f3f8a24', 'tests/test_branch_research.py': '36ad328f121b0f545a00f4657a35d21bc6adf8addd583acb73d299c03c8f8f11', 'tests/test_branch_research_boundaries.py': '34735ebc088b54f0e8f11d75871246dd215cabad15c0e0ee941092162adf905a', 'tests/test_branch_task_recovery.py': 'e02c8a1774da5b9791de73bf685b3bad5a56065519f2344fb6460544c149d108', 'tests/test_branch_worker.py': '442f073da0c06592e0b9a92d4b118db3fa35a4a04a061214ee752b6c7ab226f8', 'tests/test_build_admission.py': '9faac0972b02acb40f96023d7b5443dcb6c9973fdbdc55facc2d6ffafc11c8d2', 'tests/test_build_loop.py': '93ba41eab8af58a2d219cf09734cee83174d58812c84b11d5f6090a61885f5a5', 'tests/test_cace_adapter.py': 'e463bb9f96f0eb10ebfe7d0e16cad0b592b1b2ac025da2646eca173cac3c56d6', 'tests/test_cace_attestation.py': 'd29fad6d7e571ff3e2ff8642bfc5b36735d53f2d4449e2dcebd874622e8a45bb', 'tests/test_council.py': 'cd17a5eb96ae956792182c6127447de66ead0fb6884c2ad27a127a7c2ec21c93', 'tests/test_council_runtime.py': '10dcf51245d925cb28adb9561704cfba3dd8fc41f281686adff3e9e302438e26', 'tests/test_dot_context.py': '220bf9d83b9b6787139caf55114a3aa1a325d6763c3eaade9d063c79dbcac01c', 'tests/test_hermes_systemd.py': '60e7694d98dff1a71dd119530130fec6c0197bea60ac489ac0fd89866b4a5fcd', 'tests/test_knowledge_graph_concurrency.py': 'ff46df614a71217bd2b964b7af7cae79a785f471fa3c4d4155ff1c622ab7b2f8', 'tests/test_learning_evidence.py': '87b8048284b984fa2e4d15f977f5e1c67dd9033d4fa7264d1981dc43f1e262f7', 'tests/test_learning_evidence_evaluation.py': '602a058f1fc3629213b33c653c3496872c7035804cbba2d8a122ea1daa07015c', 'tests/test_learning_host_startup.py': '606d9eb6377bfb80264d5bf2ddeb62e2ee0bc200674d6eeab3f2f2a74c0dbfe0', 'tests/test_learning_lab_bridge.py': 'f47c5d97a7058b270133160b3a67a9808217c32d81c2ec75d989cb1ecd6d3d69', 'tests/test_learning_research_api.py': '0d2762e7435dadf7467f551255262d991ae03b44b1ee6d019021aed2a9717419', 'tests/test_learning_research_config.py': '8156479af09ab67802bc6cd8d8265c09dcc3d0f3842fa6fb6c372453811af32e', 'tests/test_learning_submission_binding.py': 'd87149b411ec48a9669239526083aa922eda2a872a759356e37fa22d4c599bad', 'tests/test_learning_titan_integration.py': '22c7d235fce3b978e38c2bb5d0a91ae9edfe43309a02e8c893ec8acecf5ebf0c', 'tests/test_local_research.py': 'e3b21ce6f26289f5b782da542d88ef55c1899d9b62895e60716a53ae5ffc427c', 'tests/test_merlin_learning_platform.py': 'c6087e869c47b18ebe9260a4c5491b1f3ce3437ef18d58db799b04d2d409ab37', 'tests/test_packet_process.py': '3be97b29961d393aefbf98387bb7b3f611a385bf6bb59e971dc3911981aadbe0', 'tests/test_packet_process_recovery.py': '81f523c1044f67509872963aa6862bb9183a69cd735bd842431990a7aadff568', 'tests/test_private_weight_status.py': '0978c137f7732ac90745a83be78273650d4d374e9ba587655156cda05bd8dffa', 'tests/test_production_runtime_boundaries.py': '341e5009c04db576ca171dff433ca9ada21766ac2fa9cb53fe3679e39bda6139', 'tests/test_project_registry.py': '38a48d714ccd5ede31f07b3a27fe7672393d3e04b95395837f5f852187a0d6f0', 'tests/test_registry_concurrent_publication.py': '3133f70a9f893c89f05ff269cbb0e60185b1f537a0184e2c5a1ad03a0b07c807', 'tests/test_review_context.py': 'd0ff532c2092bef1bcc2d034d9eb48f4d235e0bdf128c490412ea262368a2dc4', 'tests/test_storage_inventory.py': '7e38baddeb08e6eabd34ff2dae0a8d7905dcca164ea2e45f908dea18f5fb7949', 'tests/test_titan_crypto_lab.py': '4aa8a54b1bd569bd9005bbc3b7bdfde4aeb066bd30648fd4aa30cff5467e8f66', 'tests/test_titan_hermes_evidence_flow.py': 'c76eceaeefc13d05652e8fafbc7af36c759f33c653a04a1d7d8e01500c108592', 'tests/test_titan_protocol_model.py': '5afc33d34836392f34f19a6c45f501196892abd3f09192f7a3e0e590642a1b7c', 'tests/test_titan_registry_integration.py': '83b88984f1bdecbe5b13acc1353ee8f233f2abd9a5d334b830f2eecb1a4998b4', 'tests/test_virtual_dc_solver.py': '082ac5f8fe48229ba7719f053b026d14930948c176b5097fe7bb44d7ac7774e2', 'tests/test_weight_binding.py': '025fd9465194c3fc83acbbaaf079eb3a64a60f4be9bde30a0dfccf2fafa3a9bb'}, 'source_map_sha256': '548194d9fddd5a587feeb5384bf6b71f9fe7cee4976dab519725251fb2ca3654'}
BASE_SHA='d4fa47482b94c8f086b87d2c2e532a64a5874124b31283d834bc9be8350c3365'
BASE_MANIFEST_SHA='9067ebf27ee04927911310138ab7eb02075161dc030acac7028d62e2eaca56b1'
CONFIG_SHA='a25921442e2d3e463ccd685de6c67d824140b8c1592ab4fe942fb50c5d3b22e8'
SAFE_ENV={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','LANG':'C.UTF-8'}
PROJECT='dot-production-docs'
SESSION='merlin-exact-assessment-20261121'
GENERATION_SESSIONS=('merlin-exact-solver-20261121','merlin-exact-solver-20261121-format-v2')
PRESERVED_RECORDS={'dual-coder/merlin-exact-solver-20261121-format-v2/spec.json':'a1ed581deaf4afd9b899499bb2ca8f3b3d356ef32eb24528322a9dddfabe17c9','dual-coder/merlin-exact-solver-20261121-format-v2/stages/coder_a/intent.json':'1e38f8fe9262c43313a5a7fcda4cb919c74b22cd15bf2dfe6651382fc1249750','dual-coder/merlin-exact-solver-20261121-format-v2/stages/coder_a/result.json':'976ddbeeb05e3381344481417f67e98aec40955bd23be1ab08a9ed234cafd720','dual-coder/merlin-exact-solver-20261121-format-v2/stages/coder_b/failure.json':'7f33fb0482209a4dce78a2a70d7bd05b3bc98f6792fb691908fe95a1969622b1','dual-coder/merlin-exact-solver-20261121-format-v2/stages/coder_b/intent.json':'df165818fc6857c56d3ca1cb0c817db9526b575d49c1756cf5216028f0d307ad','dual-coder/merlin-exact-solver-20261121/spec.json':'02c9614c01fdbda5a585b018957b6e1f8a99acd7f8101d9641c43c26f64a923b','dual-coder/merlin-exact-solver-20261121/stages/coder_a/failure.json':'d54947397145c4bf3f06d1620409c7d657e42eaaced3e41f7e1326e7ac388fd3','dual-coder/merlin-exact-solver-20261121/stages/coder_a/intent.json':'721344715cf9790c0ae5157e40cdc0b40f9fcd0af19813c81605daa065a66194','local-research/merlin-exact-solver-20261121-format-v2/host/admission.json':'0df0c8d3bf86e1ef7a09c3bae3ea45366ff5e43f75377e4885c8a8bc0e9a547d','local-research/merlin-exact-solver-20261121-format-v2/host/oracle.json':'73ad01b8443ab3e72ee3d54c43a75ff55104b75a3d4125cc17599cced87e9abb','local-research/merlin-exact-solver-20261121-format-v2/host/provider-bootstrap.json':'7b7489297414d8304f12e8c0e28aec8ddd806704889f8b17986eac8ada0cba57','local-research/merlin-exact-solver-20261121-format-v2/host/provider-manifest.json':'35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203','local-research/merlin-exact-solver-20261121-format-v2/host/source-notes.json':'ad412f724f95df30077a6fb21503a5f291478a0048f762e2c16bddefdbfb7192','local-research/merlin-exact-solver-20261121-format-v2/host/telemetry/coder_a-689d2a1b-bd0d-481f-bbd5-339f6ac62580.json':'33504fa2acb823630a30ffc537bcf6e320128d7d3b01e037adcae77dd54c3158','local-research/merlin-exact-solver-20261121-format-v2/host/telemetry/coder_a-7c61998d-827e-49a6-a622-27fd6d6ed8c5.json':'e15e02c0b53583c0fbe62860d2481ebee03d63c4b5a8ad77d051f4ab5a936b30','local-research/merlin-exact-solver-20261121-format-v2/host/telemetry/complete-5ea2f2ec-3483-4273-b023-2d3417b85654.json':'4f2e6638f497125170bc1a7622965ef9eecaefe2b81aa6da883b0a18456ad3af','local-research/merlin-exact-solver-20261121-format-v2/host/telemetry/complete-a3cab701-e67b-41c1-b71d-5e03a1ff6d10.json':'7f87d8d93ebd385bc82d95380158c28a5c049f73f173111a4242176a1d822f57','local-research/merlin-exact-solver-20261121-format-v2/host/telemetry/replay-ae27fb87-4cfe-498b-b68e-ebd0315113de.json':'e08a8b9835034a5d390819bccfb1054f4495fba27e2afdf432bc9473925e72cb','local-research/merlin-exact-solver-20261121-format-v2/host/telemetry/replay-c524a256-00d5-400b-b8b9-2718a58124e7.json':'5592980b70c313242f4ad4db38636213b9114fa377a35307467950bbad31e7bf','local-research/merlin-exact-solver-20261121/host/admission.json':'9b505e45f2b04c09aa42278bb8107d46608353634e2cd839e5d7b0683ab5d28a','local-research/merlin-exact-solver-20261121/host/format-failure-disposition.json':'7267579a1297535970ed4f6e72d14d54024560e44f7a4b7fbae2be17a5953ede','local-research/merlin-exact-solver-20261121/host/oracle.json':'73ad01b8443ab3e72ee3d54c43a75ff55104b75a3d4125cc17599cced87e9abb','local-research/merlin-exact-solver-20261121/host/provider-bootstrap.json':'7b7489297414d8304f12e8c0e28aec8ddd806704889f8b17986eac8ada0cba57','local-research/merlin-exact-solver-20261121/host/provider-manifest.json':'35cf7ea56185126587e7dc10bb400ec53df51057407f9920d0ab03aff4299203','local-research/merlin-exact-solver-20261121/host/source-notes.json':'ad412f724f95df30077a6fb21503a5f291478a0048f762e2c16bddefdbfb7192','local-research/merlin-exact-solver-20261121/host/telemetry/coder_a-1676fb76-49ef-4834-8324-f83a4826d5a1.json':'7f5aa94746268af894e37e2fb08c0e75d09607cbef50261a80f43ca41e3cb2b9','local-research/merlin-exact-solver-20261121/host/telemetry/coder_a-37a4a269-1df8-4896-bcae-382f3a6db194.json':'eb114f6e8aaaf3495e95d5559e58abdf857564f4e3fbbe32744cf302e77f3a77','local-research/merlin-exact-solver-20261121/host/telemetry/complete-1cf181eb-6c00-41bc-83b4-cac1c12f8706.json':'69f53e7466c1b1db4e85050b4e77bd38b7a8d942d8c9329000c885969e786823','local-research/merlin-exact-solver-20261121/host/telemetry/complete-9a436a82-6c98-4a22-9b48-513f52dad2e8.json':'5aa3fcbd8d05c96da51b138dca640e8fdf00b29999c7061d471fdf379579d3ba','local-research/merlin-exact-solver-20261121/host/telemetry/replay-10fbd8af-fd7d-4a0d-a316-31229802d0d4.json':'ca64ddd307d0d1825addb8c22eda47da1496fe95338e90f55d0ce32e79ab6734','local-research/merlin-exact-solver-20261121/host/telemetry/replay-4df64e9c-82bc-4d92-bc3e-ff0f1856b1f8.json':'c6d15a1456e905660af5fe244217420be3478557c6a06442063e29e3747f7d0b','local-solver/merlin-exact-solver-20261121-format-v2/coder_a/observation.json':'6d5a612e7c7f193ea5a55655b19d4be73aaad8d5b38d63b5cec3141154378c97','local-solver/merlin-exact-solver-20261121-format-v2/coder_a/request.json':'0ea2fc73cd2050b01164af71d48d88ce0065b4800340e83fd710f35840bcd167','local-solver/merlin-exact-solver-20261121-format-v2/coder_b/observation.json':'6b14b41c08fa6e9c045ff990bfe7e1e23d23c51acd3a4a1d304eb5c3c1a7e542','local-solver/merlin-exact-solver-20261121-format-v2/coder_b/request.json':'d3311e4f0d8dff11e0ab53cc2e0e1aba969430abf7eb80f5191848b3c6274bee','local-solver/merlin-exact-solver-20261121-format-v2/host.json':'4e67ac32c495e290244e265bf22bb3d2707709d486f6f9b3cc2225fb439ee2e0','local-solver/merlin-exact-solver-20261121/coder_a/observation.json':'94eb72dd78e271475ad8e9fd3bdf4a4c68096270bfd7fa311734458272a845f5','local-solver/merlin-exact-solver-20261121/coder_a/request.json':'d3c970a3da5083d34c7ba06f9d506473bdc6ade7eb07e873871230cac3d84e6d','local-solver/merlin-exact-solver-20261121/host.json':'38051c3d2f396a4cd6e6aaea8e2dfeeb510c6a65c544f1d8aaea3abdbdc7a5fb'}
RETAINED_INPUTS_SHA256='8f7a13740d46e2bb0150ffc365e7485ae463a1a158d2bb0221d60e424c1642f2'
OLD_STATUS_SHA256={'merlin-exact-solver-20261121':'8dc2d5195dbd6c85bb547efd54b8deae2dd32910c93b468a3ef59b4310b3c7f5','merlin-exact-solver-20261121-format-v2':'114b22ac404b955e710d3e84e901ef160f4a628f6d09d7b8b5a4c50ddf819179'}
RECEIPT_PATH='local-research/' + SESSION + '/host/receipt.json'
NATIVE_WORKFLOW='.github/workflows/merlin-egm-context.yml'
NATIVE_BRANCH='merlin/platform-acceptance-20261120'
NATIVE_CONTROLLER='ops/merlin_dot/validate_egm_context_v6.py'
PROVIDER_INSPECTOR=None
EXPECTED_TOOLS={'health','context_status','context_search','context_fetch',
 'session_handoff','rsi_status','virtual_circuit_demo','research_contract',
 'research_episode_demo','mathematical_lenses_demo'}
KERNEL_CASES=sorted(('aggregate_memory_limit','cpu_time_limit',
 'detached_descendant_cleanup','fixed_program_and_actual_kernel_limits',
 'inet_socket_creation_denied','manager_wall_deadline',
 'revoked_authorization_stops_unit','tasks_max_fork_denial'))
CONTEXT_CASES=sorted(('acknowledgement_loss_after_real_process',
 'actual_cancellation_stops_process_and_fences_successor',
 'completed_process_checker_recovery_without_relaunch',
 'context_restart_actual_worker_process_and_duplicate_replay',
 'non_boolean_host_authority_cannot_start_process',
 'wrong_output_cannot_pass_or_advance_dependency'))
def sha(raw):
 return hashlib.sha256(raw).hexdigest()
def git_blob(raw):
 return hashlib.sha1(('blob %d\0' % len(raw)).encode() + raw).hexdigest()
def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),
     ensure_ascii=False,allow_nan=False).encode()
def read_json(raw):
 def pairs(items):
  result={}
  for key,value in items:
   if key in result:
    raise ValueError('duplicate receipt field')
   result[key]=value
  return result
 return json.loads(raw,object_pairs_hook=pairs)
def members(raw):
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  infos=archive.infolist()
  names=[item.filename for item in infos]
  if (len(names) != len(set(names)) or len(names) > 256
    or sum(item.file_size for item in infos) > 4 * 1024 * 1024):
   raise ValueError('bounded distinct evidence archive required')
  for item in infos:
   name=item.filename
   if (name.startswith('/') or '\\' in name or item.flag_bits & 1
     or any(part in ('','.','..') for part in name.split('/'))):
    raise ValueError('invalid evidence member')
  return {name:archive.read(name) for name in names}
def native_binding():
 return {**PINS['native'],'source_commit':PINS['source_commit'],
   'source_map_sha256':PINS['source_map_sha256']}
def check_report(report):
 n=PINS['native']
 expected={'schema':'merlin-egm-oci-validation/2','status':'succeeded',
  'run_id':n['run_id'],'run_attempt':n['run_attempt'],
  'workflow_commit':n['workflow_commit'],'runner':'cace-oci-a1',
  'source_commit':PINS['source_commit'],'source_map_sha256':PINS['source_map_sha256'],
  'source_package_sha256':n['source_package_sha256'],
  'source_kind':'exact_selected_candidate_shard','architecture':'aarch64',
  'service_unchanged':True,'qualification':False,'promotion_authority':False,
  'permissions_modified':False,'private_context_used':False,
  'production_service_modified':False,'actual_native_model_review_performed':False}
 if any(key not in report or canonical(report[key]) != canonical(value)
  for key,value in expected.items()):
  raise ValueError('accepted native report identity or scope differs')
 if (set(report.get('service_before',{})) != {'MainPID','ActiveState','SubState','UnitFileState'}
   or report['service_before'] != report.get('service_after')):
  raise ValueError('native service observations differ')
 tests=report.get('tests',{})
 ids=tests.get('executed_test_ids',[])
 if (not isinstance(ids,list) or any(not isinstance(x,str) for x in ids)
   or len(ids) != n['software_tests'] or len(ids) != len(set(ids))
   or sorted(tests.get('collection_ids',[])) != sorted(ids)
   or sha(canonical({'schema':'merlin-executed-software-tests/1','test_ids':sorted(ids)})) != n['test_inventory_sha256']):
  raise ValueError('actual native software inventory differs')
 required={'schema':'merlin-software-inventory/1','status':'succeeded',
  'tests':n['software_tests'],'collected_tests':n['software_tests'],
  'test_inventory_sha256':n['test_inventory_sha256'],'collection_sha256':n['test_inventory_sha256'],
  'passed':True,'executed':True,'source_unchanged':True,'failures':0,
  'errors':0,'skipped':0,'expected_failures':0,'unexpected_successes':0,
  'run_id':n['run_id'],'source_commit':PINS['source_commit'],
  'source_map_sha256':PINS['source_map_sha256'],'qualification':False,'promotion_authority':False}
 if any(key not in tests or canonical(tests[key]) != canonical(value) for key,value in required.items()):
  raise ValueError('native software result differs')
 for role,names in (('kernel',KERNEL_CASES),('context',CONTEXT_CASES)):
  value=report.get(role,{})
  cases=value.get('cases',[])
  if (not isinstance(cases,list) or len(cases) != len(names)
    or any(not isinstance(case,dict) or case.get('passed') is not True for case in cases)
    or sorted(case.get('name','') for case in cases) != names
    or value.get('required_case_names') != names or value.get('failed_case_ids') != []):
   raise ValueError('native named case observations differ')
  required={'status':'succeeded','tests':len(names),'passed':len(names),
   'accepted':True,'case_inventory_exact':True,'source_identity_exact':True,
   'scope_exact':True,'service_unchanged':True,'run_id':n['run_id'],
   'source_commit':PINS['source_commit'],'source_map_sha256':PINS['source_map_sha256'],
   'qualification':False,'promotion_authority':False,'permissions_modified':False,
   'production_service_modified':False}
  if any(key not in value or canonical(value[key]) != canonical(item) for key,item in required.items()):
   raise ValueError('native case identity or scope differs')
 return tests
def accepted_source(api,download):
 n=PINS['native']
 run=api('actions/runs/' + str(n['run_id']))
 expected={'id':n['run_id'],'run_attempt':n['run_attempt'],'event':'push',
  'path':NATIVE_WORKFLOW,'head_sha':n['workflow_commit'],'head_branch':NATIVE_BRANCH,
  'status':'completed','conclusion':'success'}
 if (type(run.get('run_attempt')) is not int or any(run.get(key) != value for key,value in expected.items())
   or run.get('repository',{}).get('full_name') != 'morganaspim/Cace-app'
   or run.get('head_repository',{}).get('full_name') != 'morganaspim/Cace-app'):
  raise ValueError('exact successful native run required')
 for path,identity in ((NATIVE_WORKFLOW,n['workflow_git_blob']),(NATIVE_CONTROLLER,n['controller_git_blob'])):
  if api('contents/' + path + '?ref=' + n['workflow_commit']).get('sha') != identity:
   raise ValueError('native producer source pin differs')
 item=api('actions/artifacts/' + str(n['artifact_id']))
 origin=item.get('workflow_run') or {}
 if (item.get('id') != n['artifact_id'] or item.get('name') != 'merlin-egm-%d-%d' % (n['run_id'],n['run_attempt'])
   or item.get('expired') is not False or item.get('size_in_bytes') != n['artifact_bytes']
   or item.get('digest') != 'sha256:' + n['artifact_sha256']
   or origin.get('id') != n['run_id'] or origin.get('head_sha') != n['workflow_commit']
   or origin.get('head_branch') != NATIVE_BRANCH
   or origin.get('repository_id') != run['repository']['id']
   or origin.get('head_repository_id') != run['head_repository']['id']
   or not 1 <= n['artifact_bytes'] <= 4 * 1024 * 1024):
  raise ValueError('native artifact provenance differs')
 raw=download(n['artifact_id'],n['artifact_bytes'])
 if len(raw) != n['artifact_bytes'] or sha(raw) != n['artifact_sha256']:
  raise ValueError('native artifact bytes differ')
 return checked_native_archive(raw)
def checked_native_archive(raw):
 """Data-only check after host-supplied native identity; no archive code runs."""
 n=PINS['native']
 if len(raw) != n['artifact_bytes'] or sha(raw) != n['artifact_sha256']:
  raise ValueError('native artifact bytes differ')
 archive=members(raw)
 if (sha(archive['report.json']) != n['report_sha256']
   or sha(archive['tested-source.zip']) != n['source_package_sha256']
   or sha(archive['controller.txt']) != n['controller_sha256']
   or git_blob(archive['controller.txt']) != n['controller_git_blob']):
  raise ValueError('reviewed native evidence bytes differ')
 report=read_json(archive['report.json'])
 check_report(report)
 files=members(archive['tested-source.zip'])
 manifest=read_json(files.pop('manifest.json'))
 mapping={name:sha(body) for name,body in sorted(files.items())}
 if (mapping != PINS['source_files'] or manifest.get('files') != mapping
   or manifest.get('git_blobs') != {name:git_blob(body) for name,body in files.items()}
   or sha(canonical(mapping)) != PINS['source_map_sha256']
   or manifest.get('source_commit') != PINS['source_commit']
   or manifest.get('source_map_sha256') != PINS['source_map_sha256']
   or manifest.get('schema') != 'merlin-egm-source/2'
   or manifest.get('qualification') is not False or manifest.get('promotion_authority') is not False):
  raise ValueError('full tested source identity or membership differs')
 return files,report
def projection_manifest():
 files=PINS['runtime_files']
 if (not isinstance(files,dict) or not 1 <= len(files) <= 49
   or any(not name.startswith('python/') or not name.endswith('.py')
    or PINS['source_files'].get(name) != digest for name,digest in files.items())):
  raise ValueError('runtime must be a bounded exact subset of accepted source')
 return {'schema':'merlin-dot-release/1','files':files,
   'source_repository':'Mannyspiro/expert-robot','source_base_commit':PINS['source_commit']}
def runtime_archive(files):
 manifest=projection_manifest()
 selected={name:files[name] for name in manifest['files']}
 if {name:sha(body) for name,body in selected.items()} != manifest['files']:
  raise ValueError('runtime projection content differs')
 selected['manifest.json']=(json.dumps(manifest,sort_keys=True,indent=2) + '\n').encode()
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_STORED) as archive:
  for name,body in sorted(selected.items()):
   info=zipfile.ZipInfo(name,(2026,11,21,0,0,0))
   info.external_attr=0o100644 << 16
   archive.writestr(info,body)
 return buffer.getvalue(),manifest,sha(selected['manifest.json'])
def assemble(files,unpack_verified,output):
 raw,manifest,manifest_sha=runtime_archive(files)
 unpack_verified(raw,sha(raw),output / 'candidate')
 (output / 'runtime.zip').write_bytes(raw)
 return raw,manifest,manifest_sha
def snapshot(g,release_sha,manifest_sha,expected_config=CONFIG_SHA):
 if os.geteuid() != 0:
  raise PermissionError('root-owned profile inspection requires root')
 source=g['SOURCE']
 for directory in (source,source / 'releases',g['CONFIG'].parent,g['UNIT'].parent):
  g['_root_directory'](directory)
 release=source / 'releases' / release_sha
 g['_current'](release)
 g['_regular'](g['UNIT'],expected=g['OLD_UNIT_SHA'],maximum=16000)
 config=g['_regular'](g['CONFIG'],expected=expected_config,maximum=16000)
 value=read_json(config)
 grants=value.get('grants')
 if (value.get('schema') != 'merlin-private-host/1' or value.get('project_id') != PROJECT
   or value.get('namespaces') != ['merlin','expert-robot'] or not isinstance(grants,list)
   or len(grants) != 1 or grants[0].get('uid') != 1000
   or grants[0].get('principal') != 'local-runner-opc'
   or not isinstance(grants[0].get('tools'),list)
   or len(grants[0]['tools']) != len(EXPECTED_TOOLS)
   or set(grants[0]['tools']) != EXPECTED_TOOLS):
  raise RuntimeError('existing grant profile differs from reviewed private service')
 if pwd.getpwnam('merlin-dot').pw_uid != 982 or pwd.getpwnam('opc').pw_uid != 1000:
  raise RuntimeError('service identity changed')
 g['_verify_release'](release,manifest_sha)
 return {'release_sha256':release_sha,'manifest_sha256':manifest_sha,
   'config_sha256':sha(config),'unit_sha256':g['OLD_UNIT_SHA'],
   'service_properties':g['_active'](),'grants_changed':False}
def library_probe(release):
 code="""import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from merlin.branch_research import Branch,BranchResearch
import merlin.branch_research as m
from dot_ai_os import private_runtime,local_research
for module in (m,private_runtime,local_research):
 assert Path(sys.argv[1]).resolve() in Path(module.__file__).resolve().parents
assert local_research.WORKER_PATH.is_file() and local_research.BASELINE_PATH.is_file()
p=(Branch('root','Root',2),Branch('child','Child',1,('root',)))
with tempfile.TemporaryDirectory(prefix='merlin-release-smoke-') as t:
 r=BranchResearch(Path(t)/'test.sqlite3',p)
 def evaluate(key,inputs):
  inputs.clear()
  return {'passed':True,'detail':key}
 a=r.step(evaluate,budget=2)
 assert BranchResearch(r.database,p).status()==a and a['checkpoint']['cursor']==2
print(json.dumps({'installed_entrypoint_imports':True,'restart_and_mutation_smoke':True,'model_calls':0,'canonical_state_writes':False}))
"""
 result=subprocess.run(['/usr/bin/python3','-I','-B','-c',code,str(release / 'python')],
  user=1000,group=1000,extra_groups=[],env=SAFE_ENV,cwd='/',
  capture_output=True,text=True,check=True,timeout=15)
 return read_json(result.stdout)
def fixed_ref(value,path,digest=None):
 if (not isinstance(value,dict) or set(value) != {'schema','project_id','logical_path','version','sha256'}
   or value.get('schema') != 'merlin-artifact-ref/1' or value.get('project_id') != PROJECT
   or value.get('logical_path') != path or type(value.get('version')) is not int or value['version'] != 1
   or not isinstance(value.get('sha256'),str) or len(value['sha256']) != 64
   or any(c not in '0123456789abcdef' for c in value['sha256'])
   or (digest is not None and value['sha256'] != digest)):
  raise ValueError('fixed immutable assessment reference required')
 return value
def assessment_refs():
 assessment=PINS['assessment']
 base='local-research/' + SESSION + '/host/'
 paths={'retained_inputs_ref':base+'retained-inputs.json',
  'research_plan_ref':base+'research-plan.json',
  'provider_manifest_ref':base+'provider-manifest.json',
  'provider_bootstrap_ref':base+'provider-bootstrap.json',
  'assessment_report_ref':'local-solver/'+SESSION+'/report.json',
  'report_source_ref':'context/merlin/'+sha((SESSION+':assessment-report').encode())+'/source.txt',
  'handoff_ref':'handoffs/'+SESSION+'.json'}
 if set(assessment['refs']) != set(paths):
  raise ValueError('exact assessment reference fields required')
 refs={key:fixed_ref(assessment['refs'][key],path) for key,path in paths.items()}
 fixed_ref(assessment['ref'],RECEIPT_PATH)
 if (refs['retained_inputs_ref']['sha256'] != RETAINED_INPUTS_SHA256
   or refs['provider_manifest_ref']['sha256'] != assessment['provider_files']['manifest']
   or refs['provider_bootstrap_ref']['sha256'] != assessment['provider_files']['bootstrap']
   or refs['assessment_report_ref']['sha256'] != assessment['report_sha256']
   or refs['report_source_ref']['sha256'] != assessment['report_sha256']
   or type(assessment['report_bytes']) is not int or not 1 <= assessment['report_bytes'] <= 16000):
  raise ValueError('assessment report/input/provider byte bindings differ')
 return refs
def read_wrapper(value,tool,arguments,expected_digest):
 if (not isinstance(value,dict)
   or set(value) != {'caller_uid','server_uid','transport','tool','arguments','result','result_sha256'}
   or type(value['caller_uid']) is not int or value['caller_uid'] != 1000
   or type(value['server_uid']) is not int or value['server_uid'] != 982
   or value['transport'] != 'SO_PEERCRED Unix socket'
   or value['tool'] != tool or canonical(value['arguments']) != canonical(arguments)
   or value['result_sha256'] != expected_digest
   or sha(canonical(value['result'])) != expected_digest):
  raise ValueError('complete private read wrapper differs')
 return value['result']
def check_private_results(context,handoff):
 assessment=PINS['assessment']; refs=assessment_refs()
 if not isinstance(context,dict) or not isinstance(context.get('text'),str):
  raise ValueError('complete report context text required')
 raw=context['text'].encode()
 expected={'schema':'dot-context-source-page/1','source_ref':refs['report_source_ref'],
  'start_byte':0,'end_byte':assessment['report_bytes'],'total_bytes':assessment['report_bytes'],
  'next_start_byte':None,'text':context['text'],'excerpt_sha256':assessment['report_sha256'],
  'verification_scope':'artifact-integrity-only','qualification':False}
 if (canonical(context) != canonical(expected) or len(raw) != assessment['report_bytes']
   or sha(raw) != assessment['report_sha256']
   or sha(canonical(context)) != assessment['expected_context_fetch_sha256']):
  raise ValueError('full private report bytes/result differ')
 if (not isinstance(handoff,dict) or set(handoff) != {'handoff_ref','handoff'}
   or canonical(handoff['handoff_ref']) != canonical(refs['handoff_ref'])
   or not isinstance(handoff['handoff'],dict)):
  raise ValueError('complete private handoff required')
 payload=handoff['handoff']
 if (set(payload) != {'schema','session_id','summary','next_action','source_refs','authority','qualification'}
   or payload['schema'] != 'dot-session-handoff/1' or payload['session_id'] != SESSION
   or payload['authority'] != 'context_only' or payload['qualification'] is not False
   or not isinstance(payload['summary'],str) or not isinstance(payload['next_action'],str)
   or canonical(payload['source_refs']) != canonical([refs['report_source_ref']])
   or sha(canonical(payload)) != refs['handoff_ref']['sha256']
   or sha(canonical(handoff)) != assessment['expected_handoff_result_sha256']):
  raise ValueError('exact private report handoff differs')
def check_old_status(value,session):
 if (not isinstance(value,dict) or value.get('schema') != 'dot-dual-coder-status/1'
   or value.get('session_id') != session or value.get('status') != 'incomplete'
   or value.get('qualification') is not False or value.get('promotion_authority') is not False
   or sha(canonical(value)) != OLD_STATUS_SHA256[session]):
  raise ValueError('preserved generation status changed or completed')
def check_assessment(value):
 assessment=PINS['assessment']; refs=assessment_refs()
 expected={'schema':'merlin-retained-assessment-host-receipt/1','status':'succeeded',
  'project_id':PROJECT,'session_id':SESSION,'source_commit':PINS['source_commit'],
  'source_map_sha256':PINS['source_map_sha256'],'native_validation':native_binding(),
  'invocation':assessment['invocation'],**refs,
  'report_sha256':assessment['report_sha256'],'report_bytes':assessment['report_bytes'],
  'expected_context_fetch_sha256':assessment['expected_context_fetch_sha256'],
  'expected_handoff_result_sha256':assessment['expected_handoff_result_sha256'],
  'provider_revision':assessment['provider_revision'],
  'historical_research_model_calls':3,'new_model_calls':0,'cumulative_research_model_calls':3,
  'external_model_budget_usd':0,'qualification':False,'promotion_authority':False}
 if (not isinstance(value,dict)
   or any(key not in value or canonical(value[key]) != canonical(item) for key,item in expected.items())):
  raise ValueError('retained assessment receipt differs from reviewed release contract')
 fields=set(('schema status project_id session_id source_commit source_map_sha256 native_validation invocation '
  'retained_inputs_ref research_plan_ref phases assessment_report_ref report_source_ref report_sha256 report_bytes '
  'handoff_ref private_reads expected_context_fetch_sha256 expected_handoff_result_sha256 '
  'old_generation_status_before old_generation_status_after provider_manifest_ref provider_bootstrap_ref provider_revision '
  'private_service_before private_service_after provider_service_before provider_service_after '
  'historical_research_model_calls new_model_calls cumulative_research_model_calls external_model_budget_usd '
  'preservation_before_sha256 preservation_after_sha256 prewrite_backup_sha256 qualification promotion_authority').split())
 if set(value) != fields or not isinstance(value['phases'],dict) or set(value['phases']) != {'selection','final','replay'}:
  raise ValueError('exact retained assessment receipt/phase fields required')
 pids=[]
 for phase,launches in (('selection',2),('final',2),('replay',0)):
  row=value['phases'][phase];result=row.get('result',{}) if isinstance(row,dict) else {}
  expected_phase={'schema':'merlin-retained-assessment-phase/1','phase':phase}
  expected_result={'schema':'merlin-retained-assessment-phase-result/1',
   'status':'selection_recorded' if phase=='selection' else 'completed_research_only','session_id':SESSION,
   'effects_this_call':{'inference_attempts':0,'inference_responses':0,'metadata_requests':0,'native_process_launches':launches},
   'qualification':False,'promotion_authority':False}
  if (not isinstance(row,dict) or set(row)!={'schema','phase','pid','elapsed_seconds','registry_observation','result'}
    or type(row['pid']) is not int or row['pid']<=0
    or type(row['elapsed_seconds']) not in (int,float) or not 0<=row['elapsed_seconds']<={'selection':90,'final':90,'replay':30}[phase]
    or any(key not in row or canonical(row[key])!=canonical(item) for key,item in expected_phase.items())
    or not isinstance(result,dict)
    or set(result)!=set(('schema status session_id branch_state measurement_refs observation_refs report_ref '
     'report_source_ref handoff_ref effects_this_call qualification promotion_authority').split())
    or any(key not in result or canonical(result[key])!=canonical(item) for key,item in expected_result.items())):
   raise ValueError('fresh assessment phases/effect counts differ')
  registry=row['registry_observation']
  digests=('before_inventory_sha256','after_inventory_sha256','database_before_sha256','database_after_sha256')
  if (not isinstance(registry,dict) or set(registry)!=set(digests)|{'new_artifact_refs'}
    or not isinstance(registry['new_artifact_refs'],list)
    or any(not isinstance(registry[key],str) or len(registry[key])!=64
     or any(c not in '0123456789abcdef' for c in registry[key]) for key in digests)
    or (phase=='replay' and (registry['new_artifact_refs']!=[]
     or registry['before_inventory_sha256']!=registry['after_inventory_sha256']
     or registry['database_before_sha256']!=registry['database_after_sha256']))):
   raise ValueError('assessment replay changed canonical registry')
  pids.append(row['pid'])
  for key in ('report_ref','report_source_ref','handoff_ref'):
   expected_ref=None if phase=='selection' else refs['assessment_report_ref' if key=='report_ref' else key]
   if key not in result or canonical(result[key])!=canonical(expected_ref):
    raise ValueError('phase report/read bindings differ')
 if (len(set(pids))!=3 or canonical({k:v for k,v in value['phases']['final']['result'].items() if k!='effects_this_call'})
   !=canonical({k:v for k,v in value['phases']['replay']['result'].items() if k!='effects_this_call'})):
  raise ValueError('fresh status-only assessment replay differs')
 for stem in ('private_service','provider_service','old_generation_status','preservation'):
  before=stem+'_before_sha256' if stem == 'preservation' else stem+'_before'
  after=stem+'_after_sha256' if stem == 'preservation' else stem+'_after'
  if before not in value or after not in value or canonical(value[before]) != canonical(value[after]):
   raise ValueError('assessment changed preserved state/service')
  if stem!='preservation' and (not isinstance(value[before],dict) or not value[before]):
   raise ValueError('actual preserved state/service observations required')
 for key in ('preservation_before_sha256','preservation_after_sha256','prewrite_backup_sha256'):
  if not isinstance(value[key],str) or len(value[key])!=64 or any(c not in '0123456789abcdef' for c in value[key]):
   raise ValueError('actual preservation and backup digests required')
 for when in ('before','after'):
  old=value['old_generation_status_'+when]
  if not isinstance(old,dict) or set(old) != set(GENERATION_SESSIONS):
   raise ValueError('both preserved generation statuses required')
  for session in GENERATION_SESSIONS:
   status=read_wrapper(old[session],'rsi_status',{'session_id':session},OLD_STATUS_SHA256[session])
   check_old_status(status,session)
 if not isinstance(value.get('private_reads'),dict) or set(value['private_reads']) != {'final','replay'}:
  raise ValueError('final and fresh replay private reads required')
 for reads in value['private_reads'].values():
  if not isinstance(reads,dict) or set(reads) != {'context_fetch','session_handoff'}:
   raise ValueError('exact existing private report tools required')
  context=read_wrapper(reads['context_fetch'],'context_fetch',
   {'source_ref':refs['report_source_ref'],'start_byte':0,'length_bytes':16000},
   assessment['expected_context_fetch_sha256'])
  handoff=read_wrapper(reads['session_handoff'],'session_handoff',{'session_id':SESSION},
   assessment['expected_handoff_result_sha256'])
  check_private_results(context,handoff)
 return value
def record_ref(path,digest):
 return {'schema':'merlin-artifact-ref/1','project_id':PROJECT,
   'logical_path':path,'version':1,'sha256':digest}
def load_provider_inspector(g,path):
 identity=PINS['provider_inspector']
 raw=g['_regular'](Path(path),root_owned=False,
  expected=identity['sha256'],maximum=65536)
 if sha(raw) != identity['sha256'] or git_blob(raw) != identity['git_blob']:
  raise RuntimeError('fixed provider inspector source differs')
 namespace={'__name__':'pinned_provider_inspection'}
 exec(compile(raw,'pinned-provider-inspection','exec'),namespace)
 inspector=namespace.get('inspect_ready')
 if not callable(inspector):
  raise RuntimeError('fixed provider inspector entrypoint missing')
 return inspector
def provider_probe():
 if not callable(PROVIDER_INSPECTOR):
  raise RuntimeError('fixed provider inspector was not loaded')
 value=PROVIDER_INSPECTOR()
 expected={'schema':'merlin-local-model-inspect/1','status':'ready',
  'manifest_sha256':PINS['assessment']['provider_files']['manifest'],
  'bootstrap_receipt_sha256':PINS['assessment']['provider_files']['bootstrap'],
  'inference_requests':0,'qualification':False,'external_model_cost_usd':0}
 if (not isinstance(value,dict) or not isinstance(value.get('service'),dict)
   or any(key not in value or canonical(value[key]) != canonical(item)
    for key,item in expected.items())):
  raise RuntimeError('current provider observation differs from reviewed assessment')
 return value
def assessment_probe(g,release,*,socket_status=True):
 assessment=PINS['assessment']; refs=assessment_refs(); ref=assessment['ref']
 lineage=[record_ref(name,digest) for name,digest in sorted(PRESERVED_RECORDS.items())]
 provider={}
 for name,path in (('manifest','/etc/merlin-model-provider/manifest.json'),
     ('bootstrap','/etc/merlin-model-provider/bootstrap-receipt.json')):
  provider[name+'_sha256']=sha(g['_regular'](Path(path),
   expected=assessment['provider_files'][name],maximum=256*1024))
 observation=provider_probe()
 code="""import sys,json,hashlib
sys.path.insert(0,sys.argv[1])
from dot_ai_os.private_runtime import PrivateReadOnlyRegistry
r=PrivateReadOnlyRegistry('/var/lib/merlin-dot-private/state')
ref=json.loads(sys.argv[2]);lineage=json.loads(sys.argv[3]);old=json.loads(sys.argv[4]);refs=json.loads(sys.argv[5]);report_bytes=int(sys.argv[6])
rows=r.inventory(ref['project_id'])['artifacts']
assert len(rows)<=4096 and len({x['logical_path'] for x in rows})==len(rows)
current_rows={x['logical_path']:x for x in rows}
names={name for name in current_rows if any(name.startswith(p+session+'/') for session in old for p in ('local-research/','local-solver/','dual-coder/','branch-research/')) or any(name=='handoffs/'+session+'.json' for session in old)}
assert names=={item['logical_path'] for item in lineage}
for item in lineage+list(refs.values())+[ref]:
 history=r.artifact_history(item['project_id'],item['logical_path'])
 assert len(history)==1 and type(history[0]['version']) is int and history[0]['version']==1
 current=r.artifact_ref(item['project_id'],item['logical_path'])
 assert type(current['version']) is int and current==item
 raw=r.read_artifact_ref(item,max_bytes=256*1024)['content']
 assert len(raw)<=256*1024 and hashlib.sha256(raw).hexdigest()==item['sha256']
 row=current_rows[item['logical_path']]
 assert type(row['version']) is int and row['version']==1 and row['digest']==item['sha256'] and row['size_bytes']==len(raw)
 if item['logical_path'] in (refs['report_source_ref']['logical_path'],refs['assessment_report_ref']['logical_path']):
  assert 1<=len(raw)==report_bytes<=16000
 if item['logical_path']==refs['retained_inputs_ref']['logical_path']: assert len(raw)<=32000
sys.stdout.buffer.write(raw)
"""
 result=subprocess.run(['/usr/bin/python3','-I','-B','-c',code,
  str(release/'python'),canonical(ref).decode(),canonical(lineage).decode(),
  canonical(GENERATION_SESSIONS).decode(),canonical(refs).decode(),str(assessment['report_bytes'])],
  user=982,group=1000,extra_groups=[],env=SAFE_ENV,cwd='/',capture_output=True,check=True,timeout=15)
 if len(result.stdout)>256*1024 or sha(result.stdout)!=ref['sha256']:
  raise RuntimeError('canonical assessment receipt bytes differ')
 check_assessment(read_json(result.stdout))
 answer={'receipt_ref':ref,'report_source_ref':refs['report_source_ref'],'handoff_ref':refs['handoff_ref'],
  'provider_files':provider,'provider_observation':observation,'preserved_records_verified':len(PRESERVED_RECORDS),
  'readable_by_service_uid':True,'model_calls':0,'canonical_state_writes':False}
 if socket_status:
  code="""import sys,json,hashlib
sys.path.insert(0,sys.argv[1])
from dot_ai_os.private_runtime import call_socket
def call(tool,arguments):
 reply=call_socket('/run/merlin-dot-private/tools.sock',{'schema':'merlin-private-call/1','request_id':'release-assessment-'+tool,'tool':tool,'arguments':arguments},expected_server_uid=982,timeout_seconds=5)
 assert reply.get('ok') is True and reply.get('qualification') is False and reply.get('promotion_authority') is False
 return reply['result']
source=json.loads(sys.argv[2]);session=sys.argv[3];old=json.loads(sys.argv[4])
result={'context_fetch':call('context_fetch',{'source_ref':source,'start_byte':0,'length_bytes':16000}),
 'session_handoff':call('session_handoff',{'session_id':session}),
 'old_generation_status':{item:call('rsi_status',{'session_id':item}) for item in old}}
print(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False))
"""
  result=subprocess.run(['/usr/bin/python3','-I','-B','-c',code,str(release/'python'),
   canonical(refs['report_source_ref']).decode(),SESSION,canonical(GENERATION_SESSIONS).decode()],
   user=1000,group=1000,extra_groups=[],env=SAFE_ENV,cwd='/',capture_output=True,text=True,check=True,timeout=15)
  if len(result.stdout.encode())>256*1024:
   raise RuntimeError('private assessment read output limit')
  reads=read_json(result.stdout)
  if set(reads) != {'context_fetch','session_handoff','old_generation_status'}:
   raise RuntimeError('exact private assessment read results required')
  check_private_results(reads['context_fetch'],reads['session_handoff'])
  if set(reads['old_generation_status']) != set(GENERATION_SESSIONS):
   raise RuntimeError('both old private statuses required')
  for session,status in reads['old_generation_status'].items():check_old_status(status,session)
  answer['private_reads']={'context_fetch_sha256':sha(canonical(reads['context_fetch'])),
   'handoff_result_sha256':sha(canonical(reads['session_handoff'])),
   'old_generation_status_sha256':{s:sha(canonical(v)) for s,v in reads['old_generation_status'].items()},
   'read_only_unix_route':True,'model_calls':0}
 return answer
HEALTH_WAIT="def await_health(call, clock, sleep, seconds=10):\n    start = clock()\n    attempts = 0\n    while True:\n        attempts += 1\n        try:\n            reply = call()\n        except (FileNotFoundError, ConnectionRefusedError):\n            if clock() - start >= seconds:\n                raise TimeoutError('private socket did not become ready within budget')\n            sleep(min(0.2, max(0, seconds - (clock() - start))))\n            continue\n        if (reply.get('ok') is not True or reply.get('qualification') is not False\n                or reply.get('promotion_authority') is not False\n                or reply.get('result', {}).get('transport') != 'unix'\n                or reply.get('result', {}).get('public_listener') is not False):\n            raise RuntimeError('private health contract failed; no retry')\n        return {'attempts': attempts, 'elapsed_seconds': clock() - start}\n"
def ready_probe(g,release):
 code='''import sys,json,time
sys.path.insert(0,sys.argv[1])
from dot_ai_os.private_runtime import call_socket
''' + HEALTH_WAIT + '''
def call():
 return call_socket('/run/merlin-dot-private/tools.sock', {'schema':'merlin-private-call/1','request_id':'branch-ready-health','tool':'health','arguments':{}},expected_server_uid=982,timeout_seconds=5)
print(json.dumps(await_health(call,time.monotonic,time.sleep)))
'''
 process=subprocess.run(['/usr/bin/python3','-I','-B','-c',code,str(release / 'python')],
  user=1000,group=1000,extra_groups=[],env=SAFE_ENV,cwd='/',
  capture_output=True,text=True,check=True,timeout=20)
 return {'readiness':read_json(process.stdout),'fixed_tools':g['_probe_tools'](release)}
def error_details(exc):
 result={'class':type(exc).__name__}
 if isinstance(exc,subprocess.CalledProcessError):
  detail=exc.stderr or ''
  if isinstance(detail,bytes):
   detail=detail.decode('utf-8','replace')
  result.update(returncode=exc.returncode,stderr=detail[-4000:])
 else:
  result['message']=str(exc)[:1000]
 return result
def preflight(g,unpack_verified,bundle_path,new_sha):
 before=snapshot(g,BASE_SHA,BASE_MANIFEST_SHA)
 raw=g['_regular'](Path(bundle_path),root_owned=False,expected=new_sha,maximum=13 * 1024 * 1024)
 with tempfile.TemporaryDirectory(prefix='merlin-release-preflight-') as temp:
  os.chmod(temp,0o755)
  release=Path(temp) / 'release'
  manifest=unpack_verified(raw,new_sha,release)
  if manifest != projection_manifest():
   raise RuntimeError('runtime projection manifest differs')
  library_probe(release)
  assessment=assessment_probe(g,release)
 return {'profile':before,'retained_assessment':assessment,'native_validation':native_binding(),
   'runtime_source_files':PINS['runtime_files'],'canonical_state_writes':False}
def activate(g,unpack_verified,bundle_path,new_sha,expected_preflight):
 source=g['SOURCE']; old=source / 'releases' / BASE_SHA; new=source / 'releases' / new_sha
 for directory in (source,source / 'releases',g['CONFIG'].parent):
  g['_root_directory'](directory)
 fd=os.open(source / '.research-upgrade.lock',os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,0o600)
 try:
  info=os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
   raise RuntimeError('unsafe upgrade lock')
  fcntl.flock(fd,fcntl.LOCK_EX | fcntl.LOCK_NB)
  before=preflight(g,unpack_verified,bundle_path,new_sha)
  if before != expected_preflight:
   raise RuntimeError('release prerequisites changed since validation')
  raw=g['_regular'](Path(bundle_path),root_owned=False,expected=new_sha,maximum=13 * 1024 * 1024)
  if new.exists() or new.is_symlink():
   raise RuntimeError('release already exists; inspect prior attempt before retry')
  history=g['CONFIG'].parent / 'upgrade-history'; g['_root_directory'](history)
  intent=history / ('branch-intent-' + new_sha + '.json')
  outcome=history / ('branch-result-' + new_sha + '.json')
  if any(path.exists() or path.is_symlink() for path in (intent,outcome)):
   raise RuntimeError('release history already exists; reconcile prior attempt')
  manifest=unpack_verified(raw,new_sha,new)
  if manifest != projection_manifest():
   raise RuntimeError('runtime projection manifest differs')
  manifest_sha=sha((new / 'manifest.json').read_bytes())
  g['_verify_release'](new,manifest_sha)
  record={'schema':'merlin-native-bound-private-release/1','old':before,
   'new_bundle_sha256':new_sha,'expert_source_commit':PINS['source_commit'],
   'source_map_sha256':PINS['source_map_sha256'],'runtime_source_files':PINS['runtime_files'],
   'native_validation':native_binding(),'retained_assessment_receipt_ref':PINS['assessment']['ref'],
   'unit_changed':False,'grants_changed':False,'private_state_edited_by_updater':False,
   'remote_tool_exposed':False,'model_calls':0,'qualification':False,'promotion_authority':False}
  g['_new_file'](intent,(json.dumps(record,indent=2) + '\n').encode())
  stopped=False
  try:
   snapshot(g,BASE_SHA,BASE_MANIFEST_SHA)
   stopped=True; g['_systemctl']('stop')
   g['_switch'](new,old,'branch-' + new_sha)
   g['_systemctl']('restart'); g['_wait_active']()
   probe=ready_probe(g,new)
   after=snapshot(g,new_sha,manifest_sha)
   assessment=assessment_probe(g,new)
   result={**record,'status':'upgraded','after':after,
    'fixed_tool_probe':probe,'retained_assessment':assessment,'library_probe':library_probe(new)}
  except Exception as exc:
   failure=error_details(exc)
   try:
    if stopped:g['_systemctl']('stop')
    target=os.readlink(source / 'current')
    if target == str(new):g['_switch'](old,new,'branch-rollback-' + new_sha)
    elif target != str(old):raise RuntimeError('unexpected current link; refusing blind rollback')
    if stopped:g['_systemctl']('restart')
    g['_wait_active'](); probe=ready_probe(g,old)
    after=snapshot(g,BASE_SHA,BASE_MANIFEST_SHA)
    result={**record,'status':'rolled_back','error':failure,
     'after':after,'fixed_tool_probe':probe}
   except Exception as rollback_error:
    result={**record,'status':'rollback_failed','error':failure,
      'rollback_error':error_details(rollback_error)}
  g['_new_file'](outcome,(json.dumps(result,indent=2) + '\n').encode())
  return result
 finally:
  os.close(fd)
def root_bootstrap(sources,inspector_path,expression):
 code='import hashlib,json; namespaces={}\n'
 for name in ('installer','guards','controller'):
  body=sources[name]
  code += 's=' + repr(body) + ';assert hashlib.sha256(s).hexdigest()==' + repr(sha(body)) + ';n={};exec(compile(s,' + repr('pinned-' + name) + ',"exec"),n);namespaces[' + repr(name) + ']=n\n'
 code += "g=namespaces['guards'];m=namespaces['controller'];i=namespaces['installer'];m['PROVIDER_INSPECTOR']=m['load_provider_inspector'](g," + repr(str(inspector_path)) + ');print(json.dumps(' + expression + '))'
 if len(code.encode()) > 110000:
  raise RuntimeError('root bootstrap size limit')
 return code
def run(request,api,fetch,sources,output):
 inspector=sources['provider_inspector']
 identity=PINS['provider_inspector']
 if sha(inspector) != identity['sha256'] or git_blob(inspector) != identity['git_blob']:
  raise RuntimeError('fixed provider inspector source differs')
 inspector_path=output / 'provider-inspector.py'
 with inspector_path.open('xb') as stream:
  stream.write(inspector)
 installer={}; exec(compile(sources['installer'],'pinned-installer','exec'),installer)
 evidence={}; exec(compile(sources['evidence'],'pinned-evidence','exec'),evidence)
 files,native_report=accepted_source(api,evidence['_download'])
 raw,manifest,manifest_sha=assemble(files,installer['unpack_verified'],output)
 new_sha=sha(raw)
 report={'schema':'merlin-dot-operation-receipt/1','operation':request['operation'],
  'request_id':request['request_id'],'bundle_git_blob':git_blob(raw),
  'bundle_git_blob_storage':'derived identity; archive retained in validation artifact',
  'bundle_sha256':new_sha,'source_files':manifest['files'],
  'runner':os.environ['RUNNER_NAME'],'run_id':os.environ['GITHUB_RUN_ID'],
  'workflow_commit':os.environ['GITHUB_SHA'],'qualification':False,'promotion_authority':False,
  'host_configuration_changed':False,'expert_source_commit':PINS['source_commit'],
  'source_map_sha256':PINS['source_map_sha256'],'python':sys.version,'authority_change':False,
  'scope':'private runtime projection and existing Unix read route',
  'native_validation':native_binding(),'retained_assessment_receipt_ref':PINS['assessment']['ref'],
  'tests':{**native_report['tests'],'evidence_origin':'exact reviewed full-native artifact; not a release-time rerun'},
  'model_calls':0}
 (output / 'native-validation.json').write_text(json.dumps(native_binding(),sort_keys=True,indent=2))
 def root(expression):
  code=root_bootstrap(sources,inspector_path,expression)
  result=subprocess.run(['/usr/bin/sudo','-n','/usr/bin/python3','-I','-B','-c',code],
   cwd='/',env=SAFE_ENV,capture_output=True,text=True,timeout=180)
  with (output / 'root-log.txt').open('a') as stream:
   stream.write(result.stdout + result.stderr)
  if result.returncode:
   raise RuntimeError('fixed root operation failed: ' + result.stderr[-3000:])
  return read_json(result.stdout)
 if request['operation'] == 'inspect':
  report['inspection']=root("{'snapshot':m['snapshot'](g," + repr(new_sha) + ',' + repr(manifest_sha)
   + "),'tools':m['ready_probe'](g,g['SOURCE']/'releases'/" + repr(new_sha)
   + "),'retained_assessment':m['assessment_probe'](g,g['SOURCE']/'releases'/" + repr(new_sha) + ')}')
 else:
  report['preflight']=root("m['preflight'](g,i['unpack_verified'],"
   + repr(str(output / 'runtime.zip')) + ',' + repr(new_sha) + ')')
  if request['operation'] == 'deploy':
   prior=evidence['check_validation'](request,api,git_blob(raw),new_sha,
    manifest['files'],PINS['native']['software_tests'])
   report['prior_validation']=prior
   listing=api('actions/artifacts/' + str(prior['artifact_id']))
   archive=evidence['_download'](prior['artifact_id'],listing['size_in_bytes'])
   if len(archive) != listing['size_in_bytes'] or 'sha256:' + sha(archive) != prior['archive_digest']:
    raise RuntimeError('prior validation archive changed')
   previous_raw=members(archive)['operation-receipt.json']
   if sha(previous_raw) != prior['receipt_sha256']:
    raise RuntimeError('prior validation receipt changed')
   previous=read_json(previous_raw)
   for key in ('preflight','native_validation','retained_assessment_receipt_ref','tests'):
    if previous.get(key) != report[key]:
     raise RuntimeError('exact validation prerequisites changed: ' + key)
   report['deployment']=root("m['activate'](g,i['unpack_verified'],"
    + repr(str(output / 'runtime.zip')) + ',' + repr(new_sha) + ',' + repr(report['preflight']) + ')')
   report['host_configuration_changed']=report['deployment']['status'] == 'upgraded'
   if report['deployment']['status'] != 'upgraded':
    report['status']=report['deployment']['status']
    (output / 'operation-receipt.json').write_text(json.dumps(report,indent=2))
    raise RuntimeError('release activation did not succeed')
 report['status']='succeeded'
 (output / 'operation-receipt.json').write_text(json.dumps(report,sort_keys=True,indent=2))
 print(json.dumps({key:value for key,value in report.items() if key not in ('source_files','tests')},indent=2))
 return report
