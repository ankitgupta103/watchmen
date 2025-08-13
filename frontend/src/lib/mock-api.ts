// Mock API service for machine tags
// This can be replaced with real API calls when the backend is ready

export interface TagOperation {
  machineId: number;
  tags: string[];
}

export class MockTagService {
  private static instance: MockTagService;
  private machineTags: Map<number, string[]> = new Map();

  private constructor() {
    // Initialize with some default tags for demo purposes
    this.machineTags.set(1, ["Surveillance", "High-Altitude", "Long-Range"]);
    this.machineTags.set(2, ["Patrol", "Heavy-Duty"]);
    this.machineTags.set(3, ["Weather", "Air-Quality"]);
  }

  public static getInstance(): MockTagService {
    if (!MockTagService.instance) {
      MockTagService.instance = new MockTagService();
    }
    return MockTagService.instance;
  }

  async addTags(machineId: number, newTags: string[]): Promise<boolean> {
    try {
      const existingTags = this.machineTags.get(machineId) || [];
      const updatedTags = [...existingTags, ...newTags];
      this.machineTags.set(machineId, updatedTags);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 300));
      
      console.log(`Mock API: Added tags ${newTags.join(', ')} to machine ${machineId}`);
      return true;
    } catch (error) {
      console.error('Mock API: Failed to add tags:', error);
      return false;
    }
  }

  async removeTag(machineId: number, tagToRemove: string): Promise<boolean> {
    try {
      const existingTags = this.machineTags.get(machineId) || [];
      const updatedTags = existingTags.filter(tag => tag !== tagToRemove);
      this.machineTags.set(machineId, updatedTags);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 200));
      
      console.log(`Mock API: Removed tag ${tagToRemove} from machine ${machineId}`);
      return true;
    } catch (error) {
      console.error('Mock API: Failed to remove tag:', error);
      return false;
    }
  }

  async getTags(machineId: number): Promise<string[]> {
    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 100));
      
      return this.machineTags.get(machineId) || [];
    } catch (error) {
      console.error('Mock API: Failed to get tags:', error);
      return [];
    }
  }

  async getAllMachineTags(): Promise<Map<number, string[]>> {
    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 150));
      
      return new Map(this.machineTags);
    } catch (error) {
      console.error('Mock API: Failed to get all machine tags:', error);
      return new Map();
    }
  }
}

export const mockTagService = MockTagService.getInstance();
