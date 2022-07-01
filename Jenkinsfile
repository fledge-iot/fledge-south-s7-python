node("ubuntu18-agent") {
    stage("Prerequisites"){
        sh "rm -rf fledge; git clone https://github.com/fledge-iot/fledge"
    }
    checkout scm
    stage("Run tests"){
        echo "Running tests..."
        sh "sudo ./requirements.sh"
        sh "export FLEDGE_ROOT=\$(pwd)/fledge; export PYTHONPATH=\$(FLEDGE_ROOT)/python; cd tests; python3 -m pytest"
        echo "Tests completed."
   }
}