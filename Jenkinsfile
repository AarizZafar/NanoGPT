pipeline {
    agent any

    stages {
        stage('Clone') {
            steps {
                git branch: 'main', url: 'https://github.com/AarizZafar/NanoGPT.git'
            }
        }

        stage('Stop Old Containers') {
            steps {
                sh 'docker-compose down --rmi local || true'
            }
        }

        stage('Build') {
            steps {
                sh 'docker-compose up --build -d'
            }
        }

        stage('Health Check') {
            steps {
                sleep(time: 10, unit: 'SECONDS')
                sh 'docker-compose ps'
            }
        }
    }

    post {
        success {
            echo 'Deployment successful'
        }
        failure {
            echo 'Deployment failed'
            sh 'docker-compose logs app'
        }
    }
}