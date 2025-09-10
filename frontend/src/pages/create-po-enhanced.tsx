import { useNavigate } from 'react-router-dom';
import { CreatePOWizard } from '@/components/po/create-po-wizard';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

export function CreatePOEnhanced() {
  const navigate = useNavigate();

  const handleComplete = (po: any) => {
    toast.success('Purchase order created successfully!');
    setTimeout(() => {
      navigate('/purchase-orders');
    }, 1000);
  };

  return (
    <div className="container mx-auto py-6">
      <div className="mb-6">
        <Button 
          variant="ghost" 
          onClick={() => navigate('/purchase-orders')}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Purchase Orders
        </Button>
      </div>
      
      <CreatePOWizard onComplete={handleComplete} />
    </div>
  );
}