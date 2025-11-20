package com.elecciones.backend.controller;

import com.elecciones.backend.model.VotoRegional;
import com.elecciones.backend.service.VotoRegionalService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/data/regional-votes")

public class VotoRegionalController {

    private final VotoRegionalService service;

    public VotoRegionalController(VotoRegionalService service) {
        this.service = service;
    }

    @GetMapping
    public List<VotoRegional> getAll() {
        return service.getAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<VotoRegional> getById(@PathVariable UUID id) {
        return service.getById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public VotoRegional create(@RequestBody VotoRegional voto) {
        return service.save(voto);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable UUID id) {
        service.delete(id);
    }
}
