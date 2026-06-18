package grpcclient

import (
	"cortex/internal/infrastructure/grpc/pb"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type AIServiceClient struct {
	conn        *grpc.ClientConn
	SecondBrain pb.SecondBrainServiceClient
	Homelab     pb.HomelabServiceClient
}

func NewAIServiceClient(address string) (*AIServiceClient, error) {
	conn, err := grpc.NewClient(address, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, err
	}
	return NewAIServiceClientFromConn(conn), nil
}

func NewAIServiceClientFromConn(conn *grpc.ClientConn) *AIServiceClient {
	return &AIServiceClient{
		conn:        conn,
		SecondBrain: pb.NewSecondBrainServiceClient(conn),
		Homelab:     pb.NewHomelabServiceClient(conn),
	}
}

func (c *AIServiceClient) Close() error {
	if c == nil || c.conn == nil {
		return nil
	}
	return c.conn.Close()
}
