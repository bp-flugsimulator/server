pipeline {
  agent {
    dockerfile {
      filename 'Dockerfile'
    }
    
  }
  stages {
    stage('Build') {
      steps {
        sh 'pip install --no-cache --user -r requirements.txt'
        sh 'python manage.py test'
      }
    }
  }
}