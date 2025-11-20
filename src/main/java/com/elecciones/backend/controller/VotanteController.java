package com.elecciones.backend.controller;

import com.elecciones.backend.model.Votante;
import com.elecciones.backend.service.VotanteService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/data/voters")

public class VotanteController {

    private final VotanteService service;

    public VotanteController(VotanteService service) {
        this.service = service;
    }

    @GetMapping
    public List<Votante> getAll() {
        return service.getAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Votante> getById(@PathVariable UUID id) {
        return service.getById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/dni/{dni}")
    public ResponseEntity<Votante> getByDni(@PathVariable String dni) {
        return service.getByDni(dni)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public Votante create(@RequestBody Votante votante) {
        return service.save(votante);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable UUID id) {
        service.delete(id);
    }
}
