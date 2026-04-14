# freeze_release.py - Tagging all 120+ services at once

import subprocess


from datetime import datetime

import boto3


def get_services_from_hard_env():
    """Query K8s hard env to find all deployed services."""
    cmd = """
    kubectl get deployments -n hard -o jsonpath='{range .items[*]}
      {.metadata.name},{.spec.template.spec.containers[0].image}\n{end}'
    """
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    services = {}
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        name, image = line.split(',')
        services[name] = image

    return services


def extract_digest(image_string):
    """Extract digest from image string or get it from registry."""
    if '@sha256:' in image_string:
        # Already has digest
        return image_string.split('@')[1]

    # Query ECR to get digest by tag
    # image_string looks like: 123456789.dkr.ecr.us-east-1.amazonaws.com/myapp:v1.2.3
    ecr = boto3.client('ecr', region_name='us-east-1')
    repo, tag = image_string.split('/')[-1].split(':')

    response = ecr.describe_images(
        repositoryName=repo,
        imageIds=[{'imageTag': tag}]
    )

    if response['imageDetails']:
        return response['imageDetails'][0]['imageDigest']
    return None


def tag_image_in_registry(image_string, new_tag, release_version):
    """Tag the image with release version in ECR."""
    # Parse registry and repo
    registry, image_path = image_string.split('/', 1)
    repo, old_tag = image_path.split(':')

    ecr = boto3.client('ecr', region_name='us-east-1')

    # Get manifest
    response = ecr.batch_get_image(
        repositoryName=repo,
        imageIds=[{'imageTag': old_tag}]
    )

    if not response['images']:
        print(f"  ❌ {repo}:{old_tag} not found in ECR")
        return None

    manifest = response['images'][0]['imageManifest']

    # Tag with release version
    ecr.put_image(
        repositoryName=repo,
        imageManifest=manifest,
        imageTag=f"{release_version}"  # e.g., v1.2.3
    )

    print(f"  ✓ Tagged {repo}:{release_version}")
    return ecr.describe_images(
        repositoryName=repo,
        imageIds=[{'imageTag': release_version}]
    )['imageDetails'][0]['imageDigest']


def create_release_manifest(services, release_version):
    """Create manifest file with all service digests."""
    manifest = {
        'release': release_version,
        'frozen_at': datetime.utcnow().isoformat() + 'Z',
        'services': {}
    }

    print(f"\n🔄 Processing {len(services)} services...")

    for service_name, image_string in services.items():
        print(f"\n  {service_name}:")

        digest = extract_digest(image_string)
        if not digest:
            print(f"    ⚠ Could not extract digest")
            continue

        # Tag in registry
        new_digest = tag_image_in_registry(image_string, service_name, release_version)

        manifest['services'][service_name] = {
            'image': image_string,
            'digest': new_digest or digest,
            'registry_tag': f"{release_version}"
        }

    return manifest


def commit_manifest_to_git(manifest, release_version):
    """Commit manifest to release branch in git."""
    manifest_path = '.release-manifest.yml'

    #with open(manifest_path, 'w') as f:
        #yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

    subprocess.run(['git', 'config', 'user.email', 'ci@omnicell.com'])
    subprocess.run(['git', 'config', 'user.name', 'Release Bot'])

    subprocess.run(['git', 'add', manifest_path])
    subprocess.run([
        'git', 'commit', '-m',
        f"Freeze release {release_version}: {len(manifest['services'])} services"
    ])
    subprocess.run(['git', 'push', 'origin', f'release/{release_version}'])
    subprocess.run(['git', 'tag', release_version, '-m', f'Release {release_version}'])
    subprocess.run(['git', 'push', 'origin', release_version])


def main():
    release_version = input("Release version (e.g., v1.2.3): ")

    print(f"🔒 Freezing release {release_version}...\n")

    # Step 1: Get all services from hard env
    services = get_services_from_hard_env()
    print(f"Found {len(services)} services in hard env")

    # Step 2: Create manifest (tag each service)
    # manifest = create_release_manifest(services, release_version)

    # Step 3: Commit to git
    #print(f"\n📝 Committing manifest to git...")
    #commit_manifest_to_git(manifest, release_version)

    #print(f"\n✅ Release {release_version} frozen!")
    #print(f"   Services: {len(manifest['services'])}")
    #print(f"   Manifest: .release-manifest.yml")


if __name__ == '__main__':
    main()