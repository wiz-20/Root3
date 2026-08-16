from importlib.metadata import version, PackageNotFoundError

REQUIREMENTS = {
    "pandas": "3.0.0",
    "numpy": "2.3.3",
    "matplotlib": "3.10.8",
    "jupyterlab": "4.5.4",
    "ipykernel": "6.29.5",
    "nbformat": "5.10.4",
    "pyspark": "4.2.0",
    "pymupdf": "1.28.2",
    "scikit-learn": "1.9.0",
    "streamlit": "1.61.1",
    "plotly": "6.9.0",
    "anthropic": "0.86.0",
}


def check_requirements():
    print("Checking project requirements...\n")

    all_satisfied = True

    for package, required_version in REQUIREMENTS.items():
        try:
            installed_version = version(package)

            if installed_version == required_version:
                print(
                    f"[OK] {package}: "
                    f"{installed_version}"
                )
            else:
                print(
                    f"[FAIL] {package}: "
                    f"required {required_version}, "
                    f"installed {installed_version}"
                )
                all_satisfied = False

        except PackageNotFoundError:
            print(
                f"[MISSING] {package}: "
                f"required {required_version}"
            )
            all_satisfied = False

    print()

    if all_satisfied:
        print("All requirements are satisfied.")
        return True

    print("One or more requirements are not satisfied.")
    return False


if __name__ == "__main__":
    check_requirements()