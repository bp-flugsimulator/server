pipeline {
  agent {
    docker {
      image 'python'
    }
    
  }
  stages {
    stage('Build') {
      steps {
        sh 'sudo apt install pip'
        sh 'pip -r requirements.txt'
        sh 'python manage.py test'
      }
    }
  }
}
