import os

from charmhelpers.core import hookenv
from charms.reactive import set_flag, endpoint_from_flag
from charms.reactive import when, when_not

from charms import layer


@when_not('endpoint.redis.available')
def blocked():
    goal_state = hookenv.goal_state()
    if 'redis' in goal_state['relations']:
        layer.status.waiting('waiting for redis')
    else:
        layer.status.blocked('missing relation to redis')


@when('layer.docker-resource.api-frontend-image.available')
@when('endpoint.redis.available')
@when_not('charm.kubeflow-seldon-api-frontend.started')
def start_charm():
    layer.status.maintenance('configuring container')

    image_info = layer.docker_resource.get_info('api-frontend-image')
    redis = endpoint_from_flag('endpoint.redis.available')
    redis_application_name = redis.all_joined_units[0].application_name
    redis_service_name = 'juju-{}'.format(redis_application_name)
    model = os.environ['JUJU_MODEL_NAME']

    layer.caas_base.pod_spec_set({
        'containers': [
            {
                'name': 'seldon-apiserver',
                'imageDetails': {
                    'imagePath': image_info.registry_path,
                    'username': image_info.username,
                    'password': image_info.password,
                },
                'ports': [
                    {
                        'name': 'rest',
                        'containerPort': 8080,
                    },
                    {
                        'name': 'grpc',
                        'containerPort': 5000,
                    },
                ],
                'config': {
                    'SELDON_CLUSTER_MANAGER_REDIS_HOST': redis_service_name,
                    'SELDON_CLUSTER_MANAGER_POD_NAMESPACE': model,
                    'SELDON_ENGINE_KAFKA_SERVER': 'kafka:9092',
                },
                'files': [
                ],
            },
        ],
    })

    layer.status.maintenance('creating container')
    set_flag('charm.kubeflow-seldon-api-frontend.started')
