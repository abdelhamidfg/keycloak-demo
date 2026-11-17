package demo.customer;

import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.util.List;

@Path("/api/customers")
@Produces(MediaType.APPLICATION_JSON)
public class CustomerResource {
    public record Customer(String id, String name, String email) {}
    private static final List<Customer> CUSTOMERS = List.of(
        new Customer("C100", "Aisha Hassan", "aisha@example.test"),
        new Customer("C200", "Omar Ali", "omar@example.test"));

    @GET
    public List<Customer> list() { return CUSTOMERS; }

    @GET @Path("/{id}")
    public Customer get(@PathParam("id") String id) {
        return CUSTOMERS.stream().filter(c -> c.id().equals(id)).findFirst()
            .orElseThrow(NotFoundException::new);
    }
}
