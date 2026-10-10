"""Record installed inference dependencies including their transitive versions."""
from importlib.metadata import distribution
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from training.audit import ROOT


def main():
    roots=['fastapi','uvicorn','numpy','scipy','scikit-learn','joblib','jsonschema','threadpoolctl']
    found={}
    def visit(name):
        name=canonicalize_name(name)
        if name in found:
            return
        package=distribution(name)
        found[name]=package.version
        for dependency in package.requires or []:
            requirement=Requirement(dependency)
            if requirement.marker is None or requirement.marker.evaluate({'extra':''}):
                visit(requirement.name)
    for name in roots:
        visit(name)
    (ROOT/'requirements-runtime-lock.txt').write_text('\n'.join(f'{name}=={found[name]}' for name in sorted(found))+'\n',encoding='utf-8')
    print(f'Pinned {len(found)} installed runtime dependencies for the Docker build.')


if __name__=='__main__':
    main()
