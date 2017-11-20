pipeline {
  agent {
    docker {
      image 'python'
    }
    
  }
  stages {
    stage('Build') {
      steps {
        sh 'pip install --user -r requirements.txt'
        sh 'python manage.py test'
      }
    }
  }
}
