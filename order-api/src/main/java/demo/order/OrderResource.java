package demo.order;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.*;
import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Path("/api/orders")
@ApplicationScoped
@Produces(MediaType.APPLICATION_JSON)
public class OrderResource {
    public enum Status { NEW, PROCESSING, SHIPPED, CANCELLED }
    public record Order(String id, String customerId, String item, BigDecimal total, Status status) {}
    public record Update(@NotNull Status status) {}
    private final Map<String, Order> orders = new ConcurrentHashMap<>(Map.of(
        "O100", new Order("O100", "C100", "Mechanical keyboard", new BigDecimal("249.00"), Status.NEW),
        "O200", new Order("O200", "C200", "USB-C dock", new BigDecimal("399.00"), Status.PROCESSING)));

    @GET
    public List<Order> list() {
        return orders.values().stream().sorted(Comparator.comparing(Order::id)).toList();
    }

    @GET @Path("/{id}")
    public Order get(@PathParam("id") String id) {
        Order order = orders.get(id);
        if (order == null) throw new NotFoundException();
        return order;
    }

    @PUT @Path("/{id}") @Consumes(MediaType.APPLICATION_JSON)
    public Order update(@PathParam("id") String id, @NotNull @Valid Update update) {
        Order changed = orders.computeIfPresent(id, (key, old) ->
            new Order(old.id(), old.customerId(), old.item(), old.total(), update.status()));
        if (changed == null) throw new NotFoundException();
        return changed;
    }

    @DELETE @Path("/{id}")
    public Response delete(@PathParam("id") String id) {
        if (orders.remove(id) == null) throw new NotFoundException();
        return Response.noContent().build();
    }
}
