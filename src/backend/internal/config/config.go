package config

import (
	"log"
	"os"

	"github.com/joho/godotenv"
)

const (
	EnvServerAddress    = "SERVER_ADDRESS"
	EnvDatabaseURL      = "DATABASE_URL"
	EnvLogLevel         = "LOG_LEVEL"
	EnvAIServiceAddress = "AI_SERVICE_ADDRESS"
)

type Config struct {
	ServerAddress    string
	DatabaseURL      string
	LogLevel         string
	AIServiceAddress string
}

func Load() *Config {
	// Load .env file if it exists
	if err := godotenv.Load(); err != nil {
		log.Println("Note: No .env file found or error reading it, using system environment variables")
	}

	dbUrl := os.Getenv(EnvDatabaseURL)
	if dbUrl == "" {
		log.Fatal("DATABASE_URL environment variable is required")
	}

	return &Config{
		ServerAddress:    getEnv(EnvServerAddress, ":8080"),
		DatabaseURL:      dbUrl,
		LogLevel:         getEnv(EnvLogLevel, "info"),
		AIServiceAddress: getEnv(EnvAIServiceAddress, "localhost:50051"),
	}
}

func getEnv(key, fallback string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return fallback
}
