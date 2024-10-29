timestamps {
    node("ubuntu18-agent") {
        catchError {
            checkout scm   
            dir_exists = sh (
		        script: "test -d 'tests' && echo 'Y' || echo 'N' ",
                returnStdout: true
            ).trim()

            if (dir_exists == 'N'){
                currentBuild.result= 'FAILURE'
                echo "No tests directory found! Exiting."
                return
            }

            try {
                stage("Prerequisites"){
                    // Change to corresponding CORE_BRANCH as required
                    // e.g. FOGL-xxxx, main etc.
                    sh '''
                        CORE_BRANCH='develop'
                        ${HOME}/buildFledge ${CORE_BRANCH} ${WORKSPACE}
                    '''
                }
            } catch (e) {
                currentBuild.result = 'FAILURE'
                echo "Failed to build Fledge; required to run the tests!"
                return
            }
            
            try {
                stage("Run Tests"){
                    echo "Executing tests..."
                    sh '''
                        . ${WORKSPACE}/PLUGIN_PR_ENV/bin/activate
                        export FLEDGE_ROOT=$HOME/fledge && export PYTHONPATH=$HOME/fledge/python
                        cd tests && python3 -m pytest -vv --ignore=system --ignore=api --junit-xml=test_result.xml
                    '''
                    echo "Done."
                }
            } catch (e) {
                result = "TESTS FAILED" 
                currentBuild.result = 'FAILURE'
                echo "Tests failed!"
            }
            
            try {
                stage("Publish Test Report"){
                    junit "tests/test_result.xml"
                }
            } catch (e) {
                result = "TEST REPORT GENERATION FAILED"
                currentBuild.result = 'FAILURE'
                echo "Failed to generate test reports!"
            }
        }
        stage ("Cleanup"){
            // Add here if any cleanup is required
            echo "Done."
        }
    }
}
