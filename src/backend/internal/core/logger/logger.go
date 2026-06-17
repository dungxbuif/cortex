package logger

import (
	"github.com/sirupsen/logrus"
)

var log *logrus.Logger

func Init(level string) {
	log = logrus.New()
	log.SetFormatter(&logrus.JSONFormatter{})

	lvl, err := logrus.ParseLevel(level)
	if err != nil {
		lvl = logrus.InfoLevel
	}
	log.SetLevel(lvl)
}

func Info(msg string, args ...interface{}) {
	log.Infof(msg, args...)
}

func Error(msg string, args ...interface{}) {
	log.Errorf(msg, args...)
}

func Fatal(msg string, args ...interface{}) {
	log.Fatalf(msg, args...)
}
